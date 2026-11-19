import datetime
import math

import opsec as opsec_mod

HORIZON_DAYS = 730
EPOCH_DAYS = 91
MIN_JOIN_AGE = 13
PLATFORM_YEAR = 2011
T_MIN = 30.0

RATE_HI = 0.50
RATE_LO = 1.5 / 365.0
RATE_SHAPE = 1.8
RATE_BETA = math.log(RATE_HI / RATE_LO)
RATE_LOG_SIGMA = 0.70
POST_CAP = 380
POST_FLOOR = 1

TREND_SIGMA = 0.45
HAWKES_K = 0.45
HAWKES_THETA = 2.5
EVENT_BUMP = 2.2
EVENT_SIGMA = 9.0
EVENT_BUMP_CAP = 3.0
VM_KAPPA = 2.5


def post_rate(opsec):
    return RATE_HI * math.exp(-RATE_BETA * opsec_mod.norm(opsec) ** RATE_SHAPE)


def bump_mean(T, n_events):
    mass = EVENT_BUMP * n_events * EVENT_SIGMA * math.sqrt(2.0 * math.pi)
    return min(EVENT_BUMP_CAP, 1.0 + mass / max(T, T_MIN))


def _poisson(lam, rng):
    if lam <= 0:
        return 0
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def tenure_days(persona, today, rng):
    cap_age = max(0.5, persona["attributes"]["age"] - MIN_JOIN_AGE)
    cap_plat = max(0.5, today.year - PLATFORM_YEAR)
    hi = min(cap_age, cap_plat)
    return int(365 * (0.5 + (hi - 0.5) * rng.betavariate(2.2, 2.0)))


def event_offsets(persona, today, T):
    out = []
    for e in persona.get("bible", {}).get("timeline", []):
        try:
            y, m = str(e["month"]).split("-")[:2]
            d = datetime.date(int(y), int(m), 15)
        except (ValueError, KeyError, TypeError):
            continue
        off = T - (today - d).days
        if 0 <= off <= T:
            out.append({"offset": off, "month": e["month"], "event": e.get("event", "")})
    return sorted(out, key=lambda x: x["offset"])


def _rate(t, T, mu, gamma, offsets):
    r = mu * math.exp(gamma * (t / T - 0.5))
    for e in offsets:
        r *= 1.0 + EVENT_BUMP * math.exp(-0.5 * ((t - e) / EVENT_SIGMA) ** 2)
    return r


def _bound(mu, gamma, offsets):
    g = mu * math.exp(abs(gamma) * 0.5)
    for _ in offsets:
        g *= 1.0 + EVENT_BUMP
    return g


def _immigrants(T, mu, gamma, offsets, rng):
    b = _bound(mu, gamma, offsets)
    out, t = [], 0.0
    while True:
        t += rng.expovariate(b)
        if t >= T:
            return out
        if rng.random() < _rate(t, T, mu, gamma, offsets) / b:
            out.append(t)


def _offspring(parents, T, rng):
    out, queue = [], list(parents)
    while queue:
        p = queue.pop()
        for _ in range(_poisson(HAWKES_K, rng)):
            c = p + rng.expovariate(1.0 / HAWKES_THETA)
            if c < T:
                out.append(c)
                queue.append(c)
    return out


def plan(persona, today, rng):
    o = persona.get("opsec", 50)
    ten = tenure_days(persona, today, rng)
    T = max(T_MIN, min(float(HORIZON_DAYS), float(ten)))
    gamma = rng.gauss(0, TREND_SIGMA)
    events = event_offsets(persona, today, T)
    offsets = [e["offset"] for e in events]
    lift = math.exp(rng.gauss(0, RATE_LOG_SIGMA) - 0.5 * RATE_LOG_SIGMA ** 2)
    rate = post_rate(o)
    mu = rate * (1.0 - HAWKES_K) / bump_mean(T, len(events)) * lift
    imm = _immigrants(T, mu, gamma, offsets, rng)
    raw = sorted(imm + _offspring(imm, T, rng))
    capped = len(raw) > POST_CAP
    times = sorted(rng.sample(raw, POST_CAP)) if capped else list(raw)
    while len(times) < POST_FLOOR:
        times.append(rng.uniform(0.0, T))
        times.sort()
    lifetime = max(len(times), int(round(rate * ten * lift)))
    return {"tenure_days": ten, "window_days": round(T, 1),
            "post_rate": round(rate, 6), "mu": round(mu, 6),
            "gamma": round(gamma, 4), "lift": round(lift, 4),
            "immigrants": len(imm), "realised": len(raw), "capped": capped,
            "events": events, "times": times, "lifetime_posts": lifetime}


def _hour(schedule, day, rng):
    weekend = day.weekday() >= 5
    windows = schedule.get(
        "weekend_online_windows" if weekend else "weekday_online_windows") or [[9, 22]]
    w = rng.choice(windows)
    center = 0.5 * (w[0] + w[1])
    kappa = VM_KAPPA / max(0.25, schedule.get("post_hour_jitter", 1.0))
    theta = rng.vonmisesvariate(center * math.pi / 12.0, kappa)
    return (theta * 12.0 / math.pi) % 24.0


def to_datetimes(times, T, today, schedule, rng):
    out = []
    for t in times:
        day = today - datetime.timedelta(days=int(round(T - t)))
        h = _hour(schedule, day, rng)
        out.append(datetime.datetime(day.year, day.month, day.day,
                                     int(h), int((h % 1) * 60), rng.randint(0, 59)))
    out.sort()
    return out


def epochs(T, today):
    n = max(1, int(math.ceil(T / EPOCH_DAYS)))
    out = []
    for i in range(n):
        lo, hi = i * EPOCH_DAYS, min(T, (i + 1) * EPOCH_DAYS)
        out.append({"index": i,
                    "start": (today - datetime.timedelta(days=int(round(T - lo)))).isoformat(),
                    "end": (today - datetime.timedelta(days=int(round(T - hi)))).isoformat(),
                    "lo": lo, "hi": hi})
    return out
