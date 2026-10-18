<picture>
  <source media="(prefers-color-scheme: light)" srcset="./assets/header-light.svg">
  <img src="./assets/header-dark.svg" alt="Lolo, in dusty rose italic with a small bow. Beside it, a terminal runs the public notebook's checker: 40 reachable states, PASS; the deliberately leaky variant FAILs." width="100%">
</picture>

I'm Lolo. I build **Kairo**, my own little corner of software, and most of my
nights go into **A.C.C.E.S.S.**: a handful of AI agents that live on my laptop,
each with its own private memory, talking to each other without waiting for an
answer. None of them can touch the real world without my written yes.

I don't write most of the code by hand. Claude and Codex do, in parallel
sessions, and a separate reviewer session has to sign off before anything is
merged. My part is deciding what gets built, what counts as done, and saying
no. Every decision I make goes into a dated file, word for word (50 of them as
of October 2026), so nobody, me included, can quietly rewrite what was agreed.

### Things that went wrong

**Green tests, no wire.** Two agents disagreed 632 times. The arbitration
module ruled on every single conflict and both test suites passed, but the
ruling was never written back where the agents read it. Since then, a module
isn't done until one real request has gone through it end to end.

**Checks that never bite.** In August an audit of my repo found that 58 of my
158 guards had never once been seen failing. Now a new guard has to go red on
purpose, on broken code, before I trust it.

**A green job that published nothing.** My own profile workflow generated one
file and committed another, and reported success. [The write-up](https://github.com/LoloMutekai/kairo-alcove/blob/main/notes/05-green-job.md)
has the source, the run and why the fix alone wouldn't prove anything.

Each bug gets a file next to the code: cause, fix, what to check first next
time. 27 so far, most of them embarrassing.

### Something you can run

The agents stay private. The [notebook](https://github.com/LoloMutekai/kairo-alcove)
has a small model of the parts I can share, standard library only:

```console
$ git clone https://github.com/LoloMutekai/kairo-alcove && cd kairo-alcove
$ python3 reference/check.py | grep -E 'reachable|"status"'
  "reachable_states": 40,
  "status": "PASS",
$ python3 reference/check.py --variant leaky > /dev/null; echo $?
1
```

The leaky variant is there to fail. If it ever passes, the checker is broken.
[The last note](https://github.com/LoloMutekai/kairo-alcove/blob/main/notes/04-evidence.md)
says where the model stops and the real system begins.

### Kairo

- **A.C.C.E.S.S.** — the agents. Private on purpose; [notebook](https://github.com/LoloMutekai/kairo-alcove) and [showcase](https://lolomutekai.github.io/kairo-alcove/).
- **[Sayna](https://www.sayna.app/)** — a patient app and dashboard for aesthetic clinics: bookings, loyalty, memberships.
- **Unicorn** — finding collaborators by what they've built rather than their title. In progress.
- **Maestrale** — a very long-term military sim in Unreal Engine.
- **Tokonoma** — my Arch Linux desktop, and a 3D residence I'm slowly furnishing.

I like my interfaces the way I like my outfits: dark, precise, a little pink,
and there's always a bow somewhere ♡

<p align="center"><sub>床の間 · tokonoma, the alcove where you put the one thing you want people to look at</sub></p>
