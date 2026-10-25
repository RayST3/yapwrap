# Voice examples

Run commands from the repository root. Framework examples live in
`examples/frameworks`; transport examples live in `examples/transports`.
The old numbered files have been replaced by these modules.

Each example contains its own agent configuration, speech providers, VAD, and
an explicit `yapper = YapWrap(...)` object. Server examples construct it inside
the connection handler so every call has its own agent and voice state.
No example imports setup code from another example.
After installing its dependencies, you can run a file directly as well as with
`python -m`, for example `python examples/frameworks/agno_agent.py`.

To write a new integration, start with
[custom_components.py](custom_components.py). It shows subclasses of
`BaseAgent`, `BaseSTT`, and `BaseTTS`, and runs without credentials or hardware:
`uv run python -m examples.custom_components`.

## Transport examples

All four entry points use a fresh **Agno agent with Gemini Flash Lite** for each
call, plus Silero VAD, Deepgram STT, and Cartesia TTS. The package itself keeps
these integrations optional.

PowerShell setup:

```powershell
uv sync --group examples --extra local --extra web --extra silero --extra deepgram --extra cartesia
$env:GOOGLE_API_KEY = "your-google-key"
$env:DEEPGRAM_API_KEY = "your-deepgram-key"
$env:CARTESIA_API_KEY = "your-cartesia-key"
```

`GEMINI_API_KEY` also works. `GEMINI_MODEL` defaults to
`gemini-flash-lite-latest`. These examples use paid/API services according to
your provider account; they do not promise a free tier.

| Transport | Run | Client |
| --- | --- | --- |
| [Local](transports/local.py) | `uv run python -m examples.transports.local` | Microphone, speakers, and terminal conversation |
| [FastAPI WebSocket](transports/fastapi_websocket.py) | `uv run python -m examples.transports.fastapi_websocket` | Open http://localhost:8000 |
| [Standalone WebSocket](transports/websocket.py) | `uv run python -m examples.transports.websocket` | PCM16 WebSocket on port 8765; browser instructions below |
| [WebRTC](transports/webrtc.py) | `uv run --extra webrtc python -m examples.transports.webrtc` | Open http://localhost:8000 |

WhatsApp voice calls have their own guide: [whatsapp/README.md](whatsapp/README.md).

Use one browser server at a time; both default to port 8000. FastAPI reload:

```powershell
uv run uvicorn examples.transports.fastapi_websocket:app --reload
```

For standalone WebSockets, keep its server running and serve the client from
a second terminal:

```powershell
uv run python -m http.server 8080 --bind 127.0.0.1 --directory examples/transports
```

Open http://localhost:8080/voice-client.html?ws=ws://127.0.0.1:8765 . The same
HTML client displays user transcripts and streamed agent replies. Local audio
prints a session-online message and both sides of the conversation.

The WebRTC server includes offer/answer signaling and a data channel for
transcripts. It converts incoming audio to 16 kHz mono PCM and paces outgoing
audio. This localhost demo uses host ICE candidates; remote deployments need
HTTPS, appropriate STUN/TURN configuration, and application authentication.
Stopping a call closes the signaling socket, peer, and voice session.

## Framework examples

Each framework example uses local microphone/speaker audio, so you can compare
agent integrations independently of the transport. All need the voice keys
above. The callable example only needs Deepgram and Cartesia.

Install the SDKs for the example you want. The following table lists the
packages and credentials; OpenAI examples require an explicit `OPENAI_MODEL`
available to your account, and the Claude example defaults to `CLAUDE_MODEL=sonnet`.

| Example module (under `examples.frameworks`) | Additional packages | Model credentials |
| --- | --- | --- |
| [agno_agent](frameworks/agno_agent.py) | `agno`, `google-genai` (included in the examples group) | Google/Gemini |
| [langgraph_agent](frameworks/langgraph_agent.py) | `langchain>=1`, `langchain-google-genai` | Google/Gemini |
| [pydantic_ai_agent](frameworks/pydantic_ai_agent.py) | `pydantic-ai-slim[google]` | Google/Gemini |
| [openai_agents_sdk](frameworks/openai_agents_sdk.py) | `openai-agents` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| [google_adk_agent](frameworks/google_adk_agent.py) | `google-adk` | Google/Gemini |
| [claude_agent_sdk](frameworks/claude_agent_sdk.py) | `claude-agent-sdk` | Claude Code authentication or `ANTHROPIC_API_KEY` |
| [crewai_agent](frameworks/crewai_agent.py) | `crewai[google-genai]>=1.15` | Google/Gemini |
| [llamaindex_agent](frameworks/llamaindex_agent.py) | `llama-index-core`, `llama-index-llms-google-genai` | Google/Gemini |
| [microsoft_agent](frameworks/microsoft_agent.py) | `agent-framework-openai>=1.17` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| [smolagents_agent](frameworks/smolagents_agent.py) | `smolagents[openai]` | Google/Gemini, through its OpenAI-compatible endpoint |
| [callable_agent](frameworks/callable_agent.py) | None | No model key |

For example, run the Agno or callable demos after the common setup:

```powershell
uv run python -m examples.frameworks.agno_agent
uv run python -m examples.frameworks.callable_agent
```

For other frameworks, isolated runs avoid conflicting SDK dependencies and do
not change the checkout's environment. Use Python 3.13 for broad SDK support:

```powershell
uv run --isolated --no-project --python 3.13 --with-editable ".[local,silero,deepgram,cartesia]" --with "langchain>=1" --with langchain-google-genai python -m examples.frameworks.langgraph_agent
uv run --isolated --no-project --python 3.13 --with-editable ".[local,silero,deepgram,cartesia]" --with "pydantic-ai-slim[google]" python -m examples.frameworks.pydantic_ai_agent
```

For another row, substitute its packages in the `--with` arguments and its
module name at the end. These commands install YapWrap from this checkout.
For example, CrewAI uses `--with "crewai[google-genai]>=1.15"` and
`examples.frameworks.crewai_agent`. CrewAI 1.15 requires Python below 3.14, so
keep `--python 3.13` when running it. Some frameworks impose stricter Python or
dependency constraints than YapWrap itself. Google ADK currently pins an older
OpenTelemetry range, so keep it isolated from the web environment.

LangChain now uses `langchain.agents.create_agent`, which runs on LangGraph,
instead of the deprecated `langgraph.prebuilt.create_react_agent`.
See the [official migration guide](https://docs.langchain.com/oss/python/migrate/langgraph-v1).
Pydantic AI uses [GoogleModel and GoogleProvider](https://pydantic.dev/docs/ai/models/google/).
Other adapters use the current SDK streaming interfaces:
[OpenAI Runner](https://developers.openai.com/api/docs/guides/agents/running-agents),
[ADK Runner](https://adk.dev/runtime/runconfig/),
[ClaudeSDKClient](https://code.claude.com/docs/en/agent-sdk/python),
[LlamaIndex workflows](https://developers.llamaindex.ai/python/examples/agent/agent_workflow_basic/),
and [Microsoft ResponseStream](https://learn.microsoft.com/en-us/agent-framework/concepts/agents/running-agents?tabs=python).

CrewAI and smolagents speak their final answer rather than intermediate
reasoning/tool steps. smolagents runs synchronously in a worker; interrupting
speech stops playback, but its running model call must finish before the next
turn can reuse that agent. The Claude example enables partial text and disables
tools; it is a conversation example.

History belongs to each framework. The LangGraph, OpenAI, ADK, Claude,
LlamaIndex, and Microsoft examples show their native session/context mechanism.
The other examples use their framework's default history behavior. YapWrap's
transcript log does not automatically become model context.

## Validation

The test suite covers adapter event conversion, cancellation, transcript
rendering, and a real local aiortc audio/data-channel exchange. SDK setup checks
use fake credentials and mock model metadata where construction needs it.
Live speech-provider calls, model responses, browser autoplay behavior, and
microphone/speaker quality still require a call with your own credentials.
