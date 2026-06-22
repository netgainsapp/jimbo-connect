import { useEffect, useState } from "react";
import { Play, ExternalLink, FileText } from "lucide-react";
import { blogApi, blogPublicUrl } from "../lib/api.js";
import { formatDateTime } from "../lib/utils.js";
import { useToast } from "../hooks/useToast.jsx";
import { useConfirm } from "../hooks/useConfirm.jsx";

export default function AdminBlog() {
  const toast = useToast();
  const confirm = useConfirm();
  const [flags, setFlags] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = () =>
    Promise.all([blogApi.flags(), blogApi.posts()])
      .then(([f, p]) => {
        setFlags(f);
        setPosts(p);
      })
      .catch((e) => toast.show(e.message, "error"));

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleFlag = async (name, value, confirmOn) => {
    if (value && confirmOn) {
      const ok = await confirm({
        title: "Turn on auto-publish?",
        body: "New posts that pass every guardrail will go live immediately, without review. You can turn this off again at any time.",
        confirmLabel: "Turn on",
      });
      if (!ok) return;
    }
    try {
      const updated = await blogApi.setFlag(name, value);
      setFlags(updated);
      toast.show("Saved");
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  const runNow = async () => {
    setRunning(true);
    try {
      const res = await blogApi.run();
      if (res.ok) {
        toast.show(
          res.status === "published"
            ? "Generated and published a new post."
            : "Generated a new draft for review."
        );
      } else if (res.skipped === "no_api_key") {
        toast.show("Set ANTHROPIC_API_KEY on the backend to generate.", "error");
      } else if (res.skipped === "no_unused_topic") {
        toast.show("Every topic has been used already.", "error");
      } else {
        toast.show("Nothing generated.", "error");
      }
      await load();
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setRunning(false);
    }
  };

  const publish = async (id) => {
    try {
      await blogApi.publish(id);
      toast.show("Published");
      await load();
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  const unpublish = async (id) => {
    try {
      await blogApi.unpublish(id);
      toast.show("Moved back to draft");
      await load();
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10 text-text-muted">
        Loading…
      </div>
    );
  }

  const drafts = posts.filter((p) => p.status !== "published");
  const published = posts.filter((p) => p.status === "published");

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Blog</h1>
      <p className="text-sm text-text-secondary mb-6">
        Intro Connect writes evergreen networking articles on a schedule. Review
        drafts here and control whether new posts publish on their own.
      </p>

      <div className="card p-5 mb-6">
        <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-3">
          Automation
        </div>
        <ToggleRow
          label="Auto-publish new posts"
          desc="On: posts that pass every guardrail go live immediately. Off: every post waits here as a draft for your review."
          value={!!flags?.blog_autopublish}
          onChange={(v) => toggleFlag("blog_autopublish", v, true)}
        />
        <div className="h-px bg-border-default my-3" />
        <ToggleRow
          label="Allow data-backed posts"
          desc="Off keeps the blog evergreen only. Leave off until there is enough real data to back number-driven posts."
          value={!!flags?.blog_data_posts}
          onChange={(v) => toggleFlag("blog_data_posts", v)}
        />
        <div className="h-px bg-border-default my-3" />
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div className="font-bold text-text-primary text-sm">Run now</div>
            <p className="text-sm text-text-secondary">
              Generate one post immediately instead of waiting for the schedule.
            </p>
          </div>
          <button
            onClick={runNow}
            className="btn-outline"
            disabled={running}
          >
            <Play className="w-4 h-4" />
            {running ? "Running…" : "Run now"}
          </button>
        </div>
      </div>

      <Section title={`Drafts (${drafts.length})`}>
        {drafts.length === 0 ? (
          <Empty>No drafts waiting. New posts will show up here for review.</Empty>
        ) : (
          drafts.map((p) => (
            <PostRow key={p.id} post={p} onPublish={publish} onUnpublish={unpublish} />
          ))
        )}
      </Section>

      <Section title={`Published (${published.length})`}>
        {published.length === 0 ? (
          <Empty>Nothing published yet.</Empty>
        ) : (
          published.map((p) => (
            <PostRow key={p.id} post={p} onPublish={publish} onUnpublish={unpublish} />
          ))
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-6">
      <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
        {title}
      </div>
      <div className="flex flex-col gap-3">{children}</div>
    </div>
  );
}

function Empty({ children }) {
  return <div className="card p-5 text-sm text-text-secondary">{children}</div>;
}

function PostRow({ post, onPublish, onUnpublish }) {
  const isPublished = post.status === "published";
  const blocked = (post.guardrail_reasons || []).length > 0;
  return (
    <div className="card p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <StatusBadge status={post.status} />
            <span className="font-bold text-text-primary truncate">
              {post.title}
            </span>
          </div>
          {post.summary && (
            <div className="text-sm text-text-secondary line-clamp-2 mt-1">
              {post.summary}
            </div>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          {isPublished ? (
            <>
              <a
                href={blogPublicUrl(post.slug)}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-ghost"
              >
                <ExternalLink className="w-4 h-4" /> View
              </a>
              <button onClick={() => onUnpublish(post.id)} className="btn-ghost">
                Unpublish
              </button>
            </>
          ) : (
            <button
              onClick={() => onPublish(post.id)}
              className="btn-primary"
              disabled={blocked}
              title={blocked ? "Resolve guardrail issues before publishing" : ""}
            >
              <FileText className="w-4 h-4" /> Publish
            </button>
          )}
        </div>
      </div>
      {blocked && (
        <div className="text-xs text-red-600 bg-red-50 rounded-card px-3 py-2">
          Needs attention before publishing: {post.guardrail_reasons.join(", ")}
        </div>
      )}
      <div className="text-xs text-text-muted">
        Created {formatDateTime(post.created_at)}
        {post.published_at && ` · Published ${formatDateTime(post.published_at)}`}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const published = status === "published";
  return (
    <span
      className={`text-[10px] uppercase font-bold tracking-wide px-2 py-0.5 rounded-full shrink-0 ${
        published
          ? "bg-green-100 text-green-700"
          : "bg-bg-secondary text-text-secondary"
      }`}
    >
      {published ? "Live" : "Draft"}
    </span>
  );
}

function ToggleRow({ label, desc, value, onChange }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="font-bold text-text-primary text-sm">{label}</div>
        <p className="text-sm text-text-secondary">{desc}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        aria-label={label}
        onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition shrink-0 mt-0.5 ${
          value ? "bg-primary" : "bg-border-default"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
            value ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}
