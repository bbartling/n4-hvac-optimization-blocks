# niagara4-vibe-code-addict

![Leave Temp Snip](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/vibecoder.png)


This repository provides ready-to-use **Java algorithm blocks for Niagara 4 `ProgramObjects`** (as `.bog` files) and this **README** itself, which serves as a *model context file* for Large Language Models (LLMs) such as ChatGPT or Gemini. Think of it as *the instruction manual the LLM reads before it writes code for you.*

> Ben is actively deploying and testing these `ProgramObjects` in the field, most notably the Guideline 36 algorithms, chiller demand-based start, and Optimal Start blocks built on PNNL’s latest research for energy-efficiency projects.


Also, feel free to skip the tutorials entirely and jump right into the [**Prebuilt Wiresheet Examples (.bog file format)**](https://github.com/bbartling/niagara4-vibe-code-addict/tree/develop/bog_files) for everything shown below.

Check for demonstrations on Vibe Coding on 📺
🎥 [**Talk Shop With Ben on YouTube**](https://www.youtube.com/@TalkShopWithBen)

**See also a New December 2025 [YouTube playlist](https://www.youtube.com/playlist?list=PLlNmfKmNxm1tOa8P7aBhj0zf34AIlS4CQ) on diving into optimal start/stop math and algorithms, built from daily lessons created with AI.**

---

<details>
<summary>⚙️ How to Use with AI</summary>

1. **Download all `README` markdown files** (`*.md` containing “README” in the filename) directly from GitHub including the `AGENTS.md` file.
2. **Open your LLM chat** (e.g., ChatGPT, Gemini, etc.).
3. **Upload all the `README.md` files** from your downloads folder on your computer along with your idea in mind to try. The more context the LLM has — in the form of README files — the better the results you’re likely to achieve.


**Comparison View ChatGPT and Gemeni with all READMEs uploaded**

<table>
<tr>
<td><img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/chatGPTwAllReadMes.png" width="400"/></td>
<td><img src="https://github.com/bbartling/niagara4-vibe-code-addict/blob/develop/snips/GemeniwAllReadMes.png" width="400"/></td>
</tr>
</table>

**Chat with AI what you are looking to achieve**

   > “See these READMEs — I want a `ProgramObject` that automates my chiller plant with rocket science. 🚀🤭”

4. Once the LLM confirms it understands the README, have it generate or edit your Niagara 4 `ProgramObject` code.
5. Paste the resulting Java code into Workbench’s Program Editor, make your slots for your block, and compile in the `ProgramObject` editor view.
6. **Screenshot any compile errors** using the Windows Snipping Tool and send them back into the LLM chat for review.
7. **Repeat as needed.**  ♻️ If the LLM starts generating bogus code (Gemini sometimes forgets that `ProgramObject` auto-handle imports), just remind it that Workbench generates those automatically and to reference the `README.md` file again!
8. **Simulate and test** ♻️ the logic thoroughly in your desktop office type enivornment.  When your `ProgramObject` behaves as expected, export the `.bog` file. ⚠️ **Important** ⚠️ Monitor the Application Director in Workbench for any errors.
9. **Import the tested Wiresheet** as the .bog containing the `ProgramObject` into the JACE for live field deployment.
10. Finally, **monitor JACE resources** ⚠️ **Important** ⚠️ See the section below JACE Resource Management – Best Practices for guidance on ensuring the JACE has sufficient free heap memory and acceptable CPU usage.

</details>

## 📂 Additional Guides

To keep this README concise, the detailed tutorials and algorithm implementations have been moved into separate sub‑guides.  Use the links below to navigate to the appropriate document:


- [**AGENTS.md**](AGENTS.md) — most importantly provides the AI model context and internal notes that guide how ChatGPT or other LLMs interpret this repository, generate Niagara logic, and assist in creating new `ProgramObject`s.
- [**Beginner Tutorials**](README_BEGINNER_TUTORIALS.md) — step‑by‑step examples and general algorithm blocks.
- [**GL36 Air Side Trim & Respond**](README_TRIM_RESPOND.md) — variable definitions tutorial, VAV box requests, and trim‑respond resets.
- **GL36 Air Side FDD** — coming soon! TODO.
- [**GL36 Central Plant**](README_GL36.md) — chiller plant enable logic, AHU fault detection, and other GL36‑compliant strategies.
- [**Non‑GL36 & Advanced Logic**](README_NON_GL36.md) — simplified resets and per‑chiller rotator for systems outside Guideline 36.
- [**APIs & Web Requests**](README_APIS.md) — examples for calling weather, holiday and iCalendar APIs or integrating external data science machine learning models running in docker containers.
- [**Optimal Start Algorithms**](README_OPT_START.md) — adaptive-tuning optimal start algorithms based on PNNL research, incorporating both the linear degree-per-minute model and polynomial regression.
- [**Demand‑Side Management**](README_DEMAND_SIDE_MANAGEMENT.md) — OpenADR client and PNNL‑inspired intelligent load shedding.
- [**Astronomical Clock**](README_ASTRONOMICAL_CLOCK.md) — Uses Station time and site coordinates to calculate the sun's Azimuth (compass direction) and Elevation (height in the sky).
- [**Niagara Schedules**](README_SCHEDULING.md) — for Niagara Scheduleing including ***a NEW icalender integeration*** in a `ProgramObject`!
- [**Niagara AX Notes**](NIAGARA_AX_NOTES.md) — notes on creating `ProgramObjects` in legacy Niagara AX (earlier Java-based versions).


<details>
<summary>📊 JACE Resource Management – Best Practices</summary>

To avoid Niagara runtime issues, monitor JACE system health:

![Resource Usage](https://github.com/bbartling/n4-hvac-optimization-blocks/blob/develop/snips/resource_management.png)

#### Guidelines:

* **CPU Usage:** Try to keep < 80% on average. Spikes are okay if brief.
* **Heap Usage:** Keep `heap.used` < 75% of `heap.total`.

**What to Watch:**

| Metric                       | Limit                                                 |
| ---------------------------- | ----------------------------------------------------- |
| `heap.used`                  | < 75%                                                 |
| `CPU %`                      | Avg < 80%                                             |
| `resources.category.program` | Avoid frequent `Clock.schedule()` or unbounded loops. |

</details>

<details>
<summary>🔜 Future Plans</summary> 

The AI train 🚄 shows no signs of slowing down — it’s a constantly evolving adventure.  
Recently, I hit an unexpected milestone (or limitation 😅): GitHub’s web renderer actually **truncates Markdown files over ~512 KB or 20,000 lines**. So, this project is officially “too big for one README” — which, honestly, feels like a badge of honor 😂.

The next chapter is about refining **model context** workflows and exploring how these evolving best practices might someday form a **Model Context Protocol (MCP)** for Niagara 4 — enabling AI agents to interact with `ProgramObject`s, data models, and control logic natively.  
For now, much of the process is still manual — a mix of copy-paste wizardry and Workbench perseverance — but the long game is a living, learning ecosystem of tools, agents, and context.

---

### 🧭 Vision
Someday, this project could evolve into a **full Niagara 4 module** implementing:
- **ASHRAE Guideline 36 AHU Trim & Respond**
- **GL36 AHU Fault Detection**
- **Optimal Start / Stop Blocks**



</details>


<details>
<summary>💛 Support This Work</summary>

If you make something cool or need help dont hesitate to reach out and I can add it as an example!

Also if this project helped you build something neat or saved you at least 10× in labor-hours on your Niagara BAS project with the help of AI and model context like this, and AND you’re feeling generous today, your support directly fuels Ben’s bad habits at Starbucks — but there’s absolutely no pressure. I’ve personally never donated to open-source software before — but hey, what the heck! 

| 💵 Option           | Link                                                                                                                                                                                                                                              |
| :------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 💖 **$20 fixed**    | [Donate $20](https://www.paypal.com/donate/?business=VBRBPMBZ6ZKM8&amount=20&no_recurring=0&item_name=Thank+you+for+contributing+to+help+fund+open+source+building+automation+system+%28BAS%29+software+development+donation.+&currency_code=USD) |
| ✨ **Custom amount** | [Choose any amount](https://www.paypal.com/donate/?business=VBRBPMBZ6ZKM8&no_recurring=0&item_name=Thank+you+for+contributing+to+help+fund+open+source+building+automation+system+%28BAS%29+software+development+donation.+&currency_code=USD)    |


[![Donate](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://www.paypal.com/donate/?business=VBRBPMBZ6ZKM8&no_recurring=0&item_name=Thank+you+for+contributing+to+help+fund+open+source+building+automation+system+%28BAS%29+software+development+donation.+&currency_code=USD)

</details>

---

## 📜 License

Everything here is **MIT Licensed** — free, open source, and made for the BAS community.  
Use it, remix it, or improve it — just share it forward so others can benefit too. 🥰🌍


【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.