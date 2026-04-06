## Problem Solver

Create a problem solver department



## Sales

The sales department needs a complete rewrite. I'd basically say we kick the current one and start from scratch.

The writers room really helped shaping the context and methodology and I want to build on that.

A typical sales process would be:

- A researcher dives into the topic given the context of the project, goal and instructions and writes a briefing report. This is about the industry, how comparable companies / competitors are doing it, what is currently hot or discussed topics, latest developments or trends
- A Strategist drafts a thesis about potential  outreach targets and drills down to 3-5 target areas, where a target area can be an industry sector, a cohort of people, a subset of a given mailing list and so on. Basically askin to who should we outreach right now
- A Sales Pitch Agent writes the perfect storyline for the pitch: How do we tell our story, why does it matter, why would someone care, how does it not feel like spam.
- A Profile Selector compiles for each target area a concrete set of persons to outreach to.
- A Pitch Personaliser researches the persons and adjust the storyline for them based on their interest, recent things they did and so on, together with an ideal way of targeting them based on the given set of agents available in the Department that are Outreach Specialists. At the beginning of it we only have Email outreach. Hence we need a flag for outreach on the agents and the Head of would tell the Pitch Personalizer whats available.
- This output of the Pitch Personaliser is given to Critique by a Sales QA Specialist, this would probably again break up into different specialists.
  - critically checks if the research is correct
  - verifies and challenges the thesis and target areas
  - challenges the storyline
  - double checks the profile selctor
  - verifies the storylines for the personalised pitches
- If the QA gives >= 9.5 or >= 9 and the defined number of retries the Head of Sales dispatches als Personalised Pitches to the respective outreach agents who send them.

Lets brainstorm through this!

1. Review the writers room, it's already debugged to a reasonable degree and has good points.
2. Basic line of reasoning: if we can somehow abstract things and generalize them, we do so in the base.py. Everything specific to the department (such as availabliity of outreach agents or the concrete critique flow) should go into the department using sharp interfaces and hookpoints meant for this.

