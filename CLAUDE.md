# 60XT — Body Transformation Challenge Vault

Triston's challenge started March 31, 2026. This vault tracks biometrics, nutrition, recovery, and coaching throughout a 60-day body transformation challenge.

## Vault Structure

```
plan.md              — source of truth: targets, protocols, adjustment triggers
biometrics/          — daily logs (YYYY-MM-DD.md) and weekly summaries
journal/             — coaching notes, reflections, learnings
.claude/agents/      — sub-agent descriptions
```

## Agents

- **biometrics-tracker** — pulls health data, writes daily logs, detects flags
- **coach** — day-to-day coaching, check-ins, meal decisions, progress interpretation

## Always Read First

`plan.md` is the source of truth. All targets, thresholds, and protocols live there. Check it before responding to any coaching or biometrics question.

## Key Context

- 29-year-old male, 6'2", challenge start ~201 lbs / 16.9% body fat
- Challenge start: March 31, 2026
- Newborn at home (born March 13) — sleep is fragmented but total volume is managed
- Training: Alpha class at Lifetime Fitness, 6 days/week, 6am Mon–Thu / 9:30am Fri / 10am Sat
- Diet base: chicken breast, white rice, dehydrated apples, banana pre-workout
- Primary risk: hidden fats in prepared meals inflating calories above target
- Scale noise is normal and expected — use 7-day weight average and body fat % trend
