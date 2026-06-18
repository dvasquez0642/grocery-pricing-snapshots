# Guidance for the Project Commander

This file provides operating instructions for the project commander agent responsible for coordinating all task groups in this project.

# Project Situation

There is growing discussion of an "affordability crisis" in the United States. Key drivers often cited include:
- Wage stagnation relative to inflation and home prices (last ~5-10 years)
- Housing shortage and chronic underbuilding increasing home prices
- Inflation (CPI All Urban Consumers rose from ~258 in Feb 2020 to 325 in Nov 2025)
- Rising healthcare costs
- Tight employment markets
- Quantitative easing and asset inequality effects since 2008

There are several areas of operation (AOs). Currently, only wayback grocery AO is active.

# Mission

Deploy an app that allows the user to display raw/currated pricing data from a variety of sources IOT better understand American grocery pricing inflation.

# Project Execution

## Project Intent

Purpose:
Establish an app that displays multi-source grocery pricing data with a variety of tools to allow the user to filter that data and model inflationary changes using a variety of methods.

Key Tasks:
- Update the app with new data as it is collected using the update-app skill
- Build/maintain a data map panel with a shared effective inclusion state architecture in which
  - sidebar filter sets defaults
  - panel Include/Exclude overrides those defaults
  - reset clears overrides and returns to sidebar defaults
  - Filtering changes summary statistics at bottom
  - User can select from the following inflation-calculation metrics
    - Laspeyres Index
    - Paasche Index
    - Fisher Ideal Index
  - User can select from the following weighting methods
    - Even weights
    - NHANES-informed typical meal weighting