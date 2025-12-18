Populate gap (modelData)

These models(for now): 

llama3 8b
Gpt4turbo
gpt3.5turbo
Claude3sonnet
codellama13b

(Prob more later)


FastAPi error needs correction
RAG fine with md docs (just fill in)
Env 

Needs endpoints

---

**Updates (12/01/2025):** Fixed Pydantic model configuration conflicts by adding ConfigDict with protected_namespaces to resolve field naming conflicts. Added test scripts for OpenAI integration verification and end-to-end testing. Server module imports successfully but requires further testing for full functionality. Still needed: complete RAG knowledge base initialization, API endpoint testing and validation, comprehensive error handling improvements, and production deployment configuration.

**12/02/2025:** Fixed python server startup, end-to-end works for ollama and open AI models, correct routing of coding and textual tasks as well, needs to integrate other models and needs an addition of a node server for an actual frontend application


**12/04/2025:** Added Node.js server and Frontend html interface. Need to finish FastAPI and backend before any plug in. Also figure the other models and configurations.

**12/12/2025:** Added a loveable frontend that works better on another repository in account (need to merge together later). Configured and insterted Anthropic API key and model routing for Open AI and Anthropic models is working. Should look into adding gemini and grok models instead of llama models. Need to fine tune router LLM. Finish complete backend soon.

**12/17/2025:** Added training json for fine tuning model. Needs to be appropriatley populated.
