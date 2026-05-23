# Gym Management

Frappe app for gym operations: members, membership plans, subscriptions, trainers, and attendance.

## DocTypes

- **Gym Settings** — gym name and defaults
- **Membership Plan** — plans with duration and fees
- **Gym Member** — member profiles
- **Gym Membership** — active subscriptions
- **Gym Trainer** — trainer records
- **Attendance Log** — daily check-in / check-out

## Install

```bash
cd /path/to/bench
bench get-app /path/to/gym_management  # or place under apps/
pip install -e apps/gym_management
bench --site <site> install-app gym_management
```
