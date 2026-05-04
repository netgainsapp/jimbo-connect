import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { ArrowLeft, Send, MessageCircle } from "lucide-react";
import { messagesApi } from "../lib/api.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";
import Avatar from "../components/Avatar.jsx";

const POLL_THREADS_MS = 10000;
const POLL_CHAT_MS = 4000;

export default function Messages() {
  const { userId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [threads, setThreads] = useState([]);
  const [loadingThreads, setLoadingThreads] = useState(true);

  const loadThreads = async () => {
    try {
      const t = await messagesApi.threads();
      setThreads(t);
    } catch (e) {
      // swallow
    } finally {
      setLoadingThreads(false);
    }
  };

  useEffect(() => {
    loadThreads();
    const t = setInterval(loadThreads, POLL_THREADS_MS);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1 inline-flex items-center gap-2">
        <MessageCircle className="w-6 h-6 text-primary" /> Messages
      </h1>
      <p className="text-sm text-text-secondary mb-6">
        Direct conversations with people you've met.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-[300px_1fr] gap-4 min-h-[480px]">
        <ThreadList
          threads={threads}
          loading={loadingThreads}
          activeId={userId}
          onPick={(id) => navigate(`/messages/${id}`)}
        />
        <div className="card flex flex-col">
          {userId ? (
            <Conversation
              key={userId}
              otherId={userId}
              meId={user.id}
              onSent={loadThreads}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-text-secondary text-sm">
              {threads.length === 0
                ? "No conversations yet. Open someone's profile to start one."
                : "Pick a conversation on the left."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ThreadList({ threads, loading, activeId, onPick }) {
  return (
    <div className="card divide-y divide-border-default overflow-hidden self-start">
      {loading ? (
        <div className="p-4 text-text-muted text-sm">Loading…</div>
      ) : threads.length === 0 ? (
        <div className="p-4 text-text-secondary text-sm">No threads yet.</div>
      ) : (
        threads.map((t) => {
          const p = t.other.profile || {};
          const isActive = activeId === t.other.id;
          return (
            <button
              key={t.thread_id}
              onClick={() => onPick(t.other.id)}
              className={`w-full text-left flex items-center gap-3 px-3 py-3 transition ${
                isActive ? "bg-primary/5" : "hover:bg-bg-secondary"
              }`}
            >
              <Avatar name={p.name} photoUrl={p.photo_url} size={36} />
              <div className="flex-1 min-w-0">
                <div className="font-bold text-text-primary text-sm truncate">
                  {p.name || t.other.email}
                </div>
                <div className="text-xs text-text-secondary truncate">
                  {t.last_message?.text || ""}
                </div>
              </div>
              {t.unread > 0 && (
                <span className="bg-primary text-white text-xs font-bold rounded-full min-w-[20px] h-5 px-1.5 inline-flex items-center justify-center">
                  {t.unread}
                </span>
              )}
            </button>
          );
        })
      )}
    </div>
  );
}

function Conversation({ otherId, meId, onSent }) {
  const [data, setData] = useState({ messages: [], other: null });
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const scroller = useRef(null);
  const toast = useToast();

  const load = async () => {
    try {
      const res = await messagesApi.with(otherId);
      setData(res);
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    load();
    const t = setInterval(load, POLL_CHAT_MS);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [otherId]);

  useEffect(() => {
    if (scroller.current) {
      scroller.current.scrollTop = scroller.current.scrollHeight;
    }
  }, [data.messages.length]);

  const send = async (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setSending(true);
    try {
      await messagesApi.send(otherId, trimmed);
      setText("");
      await load();
      onSent?.();
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setSending(false);
    }
  };

  const p = data.other?.profile || {};

  return (
    <>
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border-default">
        <Link
          to="/messages"
          className="md:hidden p-1 rounded-full hover:bg-bg-secondary text-text-secondary"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        {data.other && (
          <>
            <Avatar name={p.name} photoUrl={p.photo_url} size={36} />
            <div className="min-w-0">
              <div className="font-bold text-text-primary truncate">
                {p.name || data.other.email}
              </div>
              <div className="text-xs text-text-secondary truncate">
                {p.role}
                {p.role && p.company && " · "}
                {p.company}
              </div>
            </div>
          </>
        )}
      </div>
      <div
        ref={scroller}
        className="flex-1 overflow-y-auto p-4 flex flex-col gap-2 min-h-[280px]"
      >
        {loading ? (
          <div className="text-text-muted text-sm">Loading…</div>
        ) : data.messages.length === 0 ? (
          <div className="text-text-muted text-sm m-auto">
            No messages yet. Say hi.
          </div>
        ) : (
          data.messages.map((m) => {
            const mine = m.from_user_id === meId;
            return (
              <div
                key={m.id}
                className={`flex ${mine ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] px-3 py-2 rounded-card text-sm whitespace-pre-wrap break-words ${
                    mine
                      ? "bg-primary text-white"
                      : "bg-bg-secondary text-text-primary"
                  }`}
                >
                  {m.text}
                  <div
                    className={`text-[10px] mt-0.5 ${
                      mine ? "text-white/70" : "text-text-muted"
                    }`}
                  >
                    {new Date(m.sent_at).toLocaleTimeString(undefined, {
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
      <form
        onSubmit={send}
        className="p-3 border-t border-border-default flex gap-2"
      >
        <input
          className="input flex-1"
          placeholder="Type a message…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          type="submit"
          className="btn-primary"
          disabled={sending || !text.trim()}
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </>
  );
}
