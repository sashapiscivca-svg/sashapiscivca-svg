# Case studies

[Українською](CASES.uk.md) · [← Profile](README.md)

Three projects, told the way a client would want to hear them: the problem, the constraints, what went wrong, and what came out of it.

---

## hae + dal — finding people from a drone, on a $15 computer

<p align="center"><img src="https://raw.githubusercontent.com/sashapiscivca-svg/hae/main/docs/assets/hae-hero.jpg" width="640" alt="A night thermal frame from a drone at 60 m with green boxes around the people found"></p>

**The problem.** In conversations with rescuers, one idea kept coming up: a search drone that finds people by itself. Volunteer teams cannot afford expensive hardware, so the computer on board had to be a Raspberry Pi Zero 2 W, which costs about $15.

**What I did.** I designed the model architecture and chose the training data, using only open civilian datasets and no third-party weights. A month of development and training produced:

- **hae**, a thermal person detector with 313 k parameters. The int8 model is 383 KB and processes a 256×320 tile in 55 ms on the Pi.
- **hae-n-ir-ext-kdf**, a real-time companion model for forest and wilderness. In a real-time test on the Pi it found 74 % of people at under one false alarm per minute.
- **dal**, a tracker that keeps a box on a person between detections, with its own long-term benchmark, Survival@N.

**When it went off plan.** The plan was a whole line of models, from tiny to large. The data did not fit that class of models, and the bigger sizes gave no real gain. Instead of shipping a line for the sake of it, I released the one model that was clearly best, and documented why. The tracker went the same way: a classic MOSSE + Kalman tracker beat my own neural network, so the classic one is the default and the network is published as a research result.

**The result.** After the first tests the rescuers were delighted and asked for these modules for their own teams; we are now working on delivering them. Everything is public: code and weights under MIT, a model card with the limitations written first, and a demo that runs in the browser.

**What this means for your project.** I can take a model from data to a small device and measure it honestly on the real hardware, not just on a slide.

[hae](https://github.com/sashapiscivca-svg/hae) · [hae-n-ir-ext-kdf](https://github.com/sashapiscivca-svg/hae-n-ir-ext-kdf) · [dal](https://github.com/sashapiscivca-svg/dal) · [live demo](https://huggingface.co/spaces/alexshynkarenk0/hae-demo)

---

## Teul — a cozy game, shipped by cutting scope

<p align="center"><img src="https://raw.githubusercontent.com/sashapiscivca-svg/teul/main/docs/media/dusk.gif" width="640" alt="Dusk falls on the market square of Lypove and the street lanterns come on"></p>

**The idea.** I wanted to try myself in game development, and to make something warm: a small Ukrainian town, Lypove, that lives by your device's real calendar and clock.

**What I did.** The idea, the design decisions, the graphics and the overall look. Two months went into the core (a deterministic Rust engine driven by an event log, compiled to WebAssembly, with a TypeScript isometric renderer) and one more month into filling the world: a 74×114 town, eight maps around it, more than a hundred residents with schedules, moods and relationships, a daily newspaper, work, a garden, a kitchen, a driving school, holidays.

**When it went off plan.** I also built a networked world: friends, shared places, a world beyond the town, all without servers. It worked, but a serverless multiplayer product is hard to make reliable, and it was holding the release back. So I set it aside and shipped the town on its own, cleanly: no dead code, no feature flags, and old saves still open.

**The result.** One codebase runs on Android, Windows, Linux and in the browser, fully offline, with no accounts, ads or tracking. Six people played it besides me; all of them liked it and spoke warmly about it.

**What this means for your project.** I know how to cut a product down to what can ship well, and how to keep it working across platforms and updates.

[Play in the browser](https://sashapiscivca-svg.github.io/teul/) · [GitHub](https://github.com/sashapiscivca-svg/teul) · [downloads](https://github.com/sashapiscivca-svg/teul/releases/latest)

---

## Kovcheg — answers without the internet, and without electricity to spare

<p align="center"><img src="https://raw.githubusercontent.com/sashapiscivca-svg/Kovcheg/main/docs/assets/kovcheg-cli.gif" width="640" alt="Kovcheg in a terminal: a question, then the passages that answer it with their exact sources"></p>

**The idea.** It started with a question: what if I suddenly ended up in the stone age? Nobody carries all the world's knowledge in their head. I wanted a system that saves you from not knowing in a critical moment: first aid, water, food, equipment.

**What I did.** The idea and the core mechanics, over three months. Kovcheg indexes your own documents (PDF, Word, text, web pages) and answers a question with the passages that answer it and exactly where they come from. When the library has nothing relevant, it says so instead of guessing.

**When it went off plan.** The first design leaned on AI models, but they were too heavy for the simple computers people actually have when the power is out. So I made the core work with **no model at all**: fast keyword search with Ukrainian word forms taken into account, a check that the evidence is strong enough, and focused snippets. The models became an optional extra for computers that can carry them.

**The result.** It runs from a USB stick on Windows, macOS and Linux, and even in a browser tab. The feedback that stuck: *"A great thing for finding information without electricity."*

**What this means for your project.** I design for the conditions people are really in, and I make sure the product still works when the expensive part is missing.

[GitHub](https://github.com/sashapiscivca-svg/Kovcheg) · [live demo](https://huggingface.co/spaces/alexshynkarenk0/kovcheg-demo)

---

**Have a project in mind?** Write to [sasha.piscivca@gmail.com](mailto:sasha.piscivca@gmail.com): what you want to build, for whom and by when.
