# Demo database seed

The reusable demo seed lives in `scripts/seed_demo.py`.

Run it from the repository root after configuring the database:

```powershell
myenv\Scripts\python.exe -m scripts.seed_demo
```

Or, when the virtual environment is already active:

```bash
python -m scripts.seed_demo
```

## Demo credentials

College slug:

```text
jnan-vikas-mandal-demo
```

Admin:

```text
username: demo_admin
password: Demo@123
```

Teachers:

```text
username: demo_teacher1
username: demo_teacher2
username: demo_teacher3
password: Demo@123
```

## What is seeded

- 1 demo college: Jnan Vikas Mandal
- 1 demo administrator
- 3 demo teachers
- 3 BCA class sections: 1A, 1B, 2A
- 30 demo students, 10 per class
- 3 teacher-to-class assignments
- 4 demo lectures: completed, active, upcoming, cancelled
- 40 attendance records containing both Present and Absent statuses

## Re-running the seed

The college, admin, teachers, classes, assignments, and students are upserted
using their demo identifiers. The four demo lectures are rebuilt on every run,
along with their demo attendance records, so the active lecture is always
relative to the current India-local time.

Only records belonging to the demo college and the known demo identifiers are
touched. Existing non-demo college data is not deleted.

## Timing scenarios

After every seed run:

- **Active** is scheduled from 15 minutes before seed time until 30 minutes after seed time.
- **Completed** is yesterday from 10:00 to 11:00.
- **Upcoming** is tomorrow from 09:00 to 10:00.
- **Cancelled** is tomorrow from 11:00 to 12:00.

This makes the teacher attendance timing rule easy to verify: attendance can be
marked during the active lecture, but a teacher receives an error for the
completed or upcoming lecture. The cancelled lecture is rejected because of
its cancelled status.
