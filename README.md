�

🔁 Self-Healing RAG
A Retrieval-Augmented Generation pipeline that critiques its own answers — and retries instead of hallucinating.
� � � � � � � �
🚀 Live Demo · Report Bug · Request Feature
�

📖 Overview
Most RAG pipelines retrieve documents, stuff them into a prompt, and generate an answer — full stop. If the retrieved context is thin or the generator drifts, the result is a confident hallucination with no safety net.
Self-Healing RAG adds a closed loop: a critic model checks whether the generated answer is actually grounded in the retrieved documents. If it isn't, the pipeline reformulates the query and retries — up to a configurable retry limit — before falling back gracefully. You can watch this entire decision process happen live in the "Self-healing trace" panel of the app.
TL;DR
🔁 Retries instead of hallucinating — a critic model checks groundedness after every generation; if the answer isn't supported by the retrieved context, the pipeline reformulates the query and tries again, up to a configurable limit, before an honest fallback.
🧠 Two-model split by design — a fast model handles groundedness critique while a larger model handles generation, so the safety check doesn't add generation-level latency.
🔍 The reasoning is visible, not a black box — the self-healing trace panel shows every retrieval, critique, and retry step live, not just the final answer.
🏗️ Built as a real cyclical graph, not a linear chain — implemented as a LangGraph StateGraph with an explicit retrieve → generate → critique → route loop.
🎥 Demo
�
￼ 

�
📷 Screenshots + 🎥 full walkthrough video 

�
￼ ￼ 

�


https://github.com/user-attachments/assets/64c62ba5-f80b-48aa-86fc-e30ab216332d
�

✨ Features
🔄 Cyclical self-correction loop — built as a StateGraph in LangGraph, not a linear chain
🧠 Two-model split — a fast LLaMA 3.1 8B critic judges groundedness while LLaMA 3.3 70B (via Groq) handles generation
📚 PDF ingestion — upload any PDF and query it directly from the sidebar
🔍 Transparent reasoning — expand the self-healing trace to see every retrieval, critique, and retry step in real time
🛡️ Graceful fallback — after the retry budget is exhausted, the app returns an honest fallback answer instead of guessing
🗄️ Vector storage via Chroma
🏗️ Architecture
flowchart TD
    A[User Query] --> B[Retrieve from Chroma]
    B --> C["Generate Answer (LLaMA 3.3 70B)"]
    C --> D{"Critic: Is it grounded? (LLaMA 3.1 8B)"}
    D -- Grounded --> E[✅ Accept Answer]
    D -- "Not grounded, retries left" --> F["Reformulate Query"]
    F --> B
    D -- Retries exhausted --> G[⚠️ Fallback Answer]
The loop is implemented as a cyclical LangGraph StateGraph: retrieve → generate → critique → route, where route_after_critique decides whether to accept, retry, or fallback based on the critic's groundedness verdict and the current retry count.
🚀 Getting Started
Prerequisites
Python 3.10+
A Groq API key
Installation
# Clone the repo
git clone https://github.com/ayush-s-tomar/self-healing-rag.git
cd self-healing-rag/streamlit_app

# Install dependencies
pip install -r requirements.txt

# Set your Groq API key
export GROQ_API_KEY="your-key-here"   # on Windows: setx GROQ_API_KEY "your-key-here"

# Run the app
streamlit run app.py
The app will be available at http://localhost:8501.
Note (hosted demo only, not local runs): on free/constrained CPU hosting, PDF ingestion and the first query may take 20–30 seconds while models warm up. This doesn't apply when running locally on your own machine.
🧰 Project Structure
self-healing-rag/
├── streamlit_app/
│   ├── app.py            # Streamlit UI entry point
│   ├── graph.py           # LangGraph StateGraph definition
│   ├── nodes.py            # Node functions: generate, critique, fallback, routing
│   ├── retrieval.py        # Chroma-backed retrieval logic
│   └── requirements.txt
├── assets/                 # Screenshots and media used in this README
├── .github/workflows/ci.yml
├── LICENSE
└── README.md
🛠️ Tech Stack
Layer
Tool
Orchestration
LangGraph
LLM inference
Groq (LLaMA 3.1 8B / 3.3 70B)
Vector store
Chroma
UI
Streamlit
Deployment
Hugging Face Spaces (Docker)
🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.
Fork the project
Create your feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add some amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request
📄 License
Distributed under the MIT License. See LICENSE for more information.
🙋 Author
Ayush Singh Tomar GitHub · LinkedIn
�
If this project helped you, consider giving it a ⭐! 
