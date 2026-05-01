"use client";
import { useEffect, useState, useCallback } from "react";
import {
  chatterApi, ActivityOut, ActivityType,
  TYPE_ICON, TYPE_COLOR, timeAgo,
} from "@/lib/chatter";

interface Props {
  referenceType: string;
  referenceId: string;
  currentUser?: string;
  compact?: boolean;
}

function Avatar({ name, size = "md" }: { name: string; size?: "sm" | "md" }) {
  const sz = size === "sm" ? "w-5 h-5 text-xs" : "w-7 h-7 text-sm";
  const colors = ["bg-blue-500", "bg-purple-500", "bg-green-500", "bg-orange-500", "bg-pink-500"];
  const color = colors[name.charCodeAt(0) % colors.length];
  return (
    <div className={`${sz} ${color} rounded-full text-white flex items-center justify-center font-bold shrink-0`}>
      {name.charAt(0).toUpperCase()}
    </div>
  );
}

function CommentThread({ activity, currentUser, onUpdate }: {
  activity: ActivityOut; currentUser: string; onUpdate: () => void;
}) {
  const [replyText, setReplyText] = useState("");
  const [showReply, setShowReply] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const visibleComments = activity.comments.filter(c => !c.deleted_flag);

  const postReply = async () => {
    if (!replyText.trim()) return;
    await chatterApi.postComment(activity.activity_id, {
      user_name: currentUser, message: replyText,
    });
    setReplyText("");
    setShowReply(false);
    onUpdate();
  };

  const saveEdit = async (commentId: string) => {
    await chatterApi.editComment(commentId, editText);
    setEditing(null);
    onUpdate();
  };

  const deleteComment = async (commentId: string) => {
    if (!confirm("Delete this comment?")) return;
    await chatterApi.deleteComment(commentId);
    onUpdate();
  };

  return (
    <div>
      {visibleComments.length > 0 && (
        <div className="mt-2.5 border-l-2 border-gray-200 pl-3 space-y-2">
          {activity.comments.map(c => {
            if (c.deleted_flag) return null;
            return (
              <div key={c.comment_id} className="group flex items-start gap-2">
                <Avatar name={c.user_name ?? "U"} size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-gray-700">{c.user_name ?? "User"}</span>
                    <span className="text-xs text-gray-400">{timeAgo(c.created_at)}</span>
                    {c.edited_at && <span className="text-xs text-gray-300">(edited)</span>}
                    {c.user_name === currentUser && !editing && (
                      <div className="hidden group-hover:flex gap-2 ml-auto">
                        <button onClick={() => { setEditing(c.comment_id); setEditText(c.message); }}
                          className="text-xs text-gray-400 hover:text-blue-600">Edit</button>
                        <button onClick={() => deleteComment(c.comment_id)}
                          className="text-xs text-gray-400 hover:text-red-500">Delete</button>
                      </div>
                    )}
                  </div>
                  {editing === c.comment_id ? (
                    <div className="flex gap-1 mt-1">
                      <input className="flex-1 border rounded px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                        value={editText} onChange={e => setEditText(e.target.value)} />
                      <button onClick={() => saveEdit(c.comment_id)}
                        className="text-xs text-blue-600 font-medium hover:underline">Save</button>
                      <button onClick={() => setEditing(null)}
                        className="text-xs text-gray-400 hover:underline">Cancel</button>
                    </div>
                  ) : <p className="text-xs text-gray-600 mt-0.5">{c.message}</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showReply ? (
        <div className="flex gap-2 mt-2.5">
          <Avatar name={currentUser} size="sm" />
          <div className="flex-1 flex gap-1">
            <input
              className="flex-1 border rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              placeholder="Write a reply… @mention to notify someone"
              value={replyText}
              onChange={e => setReplyText(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") postReply(); }}
              autoFocus
            />
            <button onClick={postReply} className="text-xs bg-blue-600 text-white px-2 rounded hover:bg-blue-700">Post</button>
            <button onClick={() => setShowReply(false)} className="text-xs text-gray-400">Cancel</button>
          </div>
        </div>
      ) : (
        <button onClick={() => setShowReply(true)}
          className="mt-1.5 text-xs text-gray-400 hover:text-blue-600 transition-colors">
          Reply
        </button>
      )}
    </div>
  );
}

function ActivityCard({ activity, currentUser, onUpdate }: {
  activity: ActivityOut; currentUser: string; onUpdate: () => void;
}) {
  const isComment = activity.activity_type === "comment";
  const cardClass = isComment
    ? "bg-white border rounded-lg p-3"
    : "bg-gray-50 border border-dashed rounded-lg px-3 py-2";

  return (
    <div className={cardClass}>
      <div className="flex items-start gap-2.5">
        <div className={`text-sm rounded-full px-1.5 py-1 leading-none ${TYPE_COLOR[activity.activity_type]}`}>
          {TYPE_ICON[activity.activity_type]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-800">{activity.created_by ?? "System"}</span>
            {activity.is_pinned && (
              <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">📌 Pinned</span>
            )}
            <span className="text-xs text-gray-400 ml-auto">{timeAgo(activity.created_at)}</span>
          </div>
          <p className={`text-xs ${isComment ? "text-gray-500" : "text-gray-700 font-medium"} mb-1`}>
            {activity.title}
          </p>
          {activity.message && (
            <p className="text-sm text-gray-700 whitespace-pre-wrap break-words">{activity.message}</p>
          )}
          {activity.mentions.length > 0 && (
            <div className="flex gap-1 mt-1 flex-wrap">
              {activity.mentions.map(m => (
                <span key={m.mention_id} className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">
                  @{m.mentioned_user}
                </span>
              ))}
            </div>
          )}
          {activity.attachments.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {activity.attachments.map(att => (
                <span key={att.attachment_id}
                  className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-600 rounded px-2 py-0.5 border">
                  📎 {att.file_name}
                </span>
              ))}
            </div>
          )}
          {isComment && (
            <CommentThread activity={activity} currentUser={currentUser} onUpdate={onUpdate} />
          )}
        </div>
      </div>
    </div>
  );
}

export default function ChatterTimeline({
  referenceType, referenceId, currentUser = "User", compact = false,
}: Props) {
  const [activities, setActivities] = useState<ActivityOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [posting, setPosting] = useState(false);
  const [showAttach, setShowAttach] = useState(false);
  const [attachName, setAttachName] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    chatterApi.listActivities({
      reference_type: referenceType,
      reference_id: referenceId,
      per_page: 100,
    }).then(data => setActivities(data.items)).finally(() => setLoading(false));
  }, [referenceType, referenceId]);

  useEffect(() => { load(); }, [load]);

  const post = async () => {
    if (!text.trim()) return;
    setPosting(true);
    try {
      await chatterApi.createActivity({
        reference_type: referenceType,
        reference_id: referenceId,
        activity_type: "comment",
        title: "Comment",
        message: text,
        created_by: currentUser,
      });
      setText("");
      load();
    } finally { setPosting(false); }
  };

  const attach = async (actId: string) => {
    if (!attachName.trim() || !actId) return;
    await chatterApi.addAttachment(actId, {
      file_name: attachName, uploaded_by: currentUser,
    });
    setAttachName("");
    setShowAttach(false);
    load();
  };

  // Group by date (newest-first already from API, reverse for display)
  const ordered = [...activities].reverse();
  const byDate: Record<string, ActivityOut[]> = {};
  ordered.forEach(a => {
    const d = new Date(a.created_at).toLocaleDateString("en-GB", {
      day: "numeric", month: "short", year: "numeric",
    });
    byDate[d] = byDate[d] ?? [];
    byDate[d].push(a);
  });

  return (
    <div className={compact ? "space-y-3" : "space-y-4"}>
      {/* Post box */}
      <div className="flex gap-2 items-start">
        <Avatar name={currentUser} />
        <div className="flex-1 space-y-1.5">
          <textarea
            className="w-full border rounded px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
            rows={compact ? 1 : 2}
            placeholder="Add a comment… Use @name to mention someone (Ctrl+Enter to post)"
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) post(); }}
          />
          <div className="flex items-center gap-2">
            <button onClick={post} disabled={!text.trim() || posting}
              className="rounded bg-blue-600 px-3 py-1 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {posting ? "Posting…" : "Post"}
            </button>
            <button onClick={() => setShowAttach(s => !s)}
              className="text-xs text-gray-500 hover:text-gray-700">📎 Attach</button>
          </div>
          {showAttach && (
            <div className="flex gap-2">
              <input className="flex-1 border rounded px-2 py-1 text-sm"
                placeholder="File name (e.g. report.pdf)"
                value={attachName} onChange={e => setAttachName(e.target.value)} />
              <button onClick={() => {
                if (activities.length > 0) attach(activities[0].activity_id);
                else alert("Post a comment first, then attach.");
              }} className="rounded bg-gray-700 px-3 py-1 text-sm text-white hover:bg-gray-600">
                Upload
              </button>
              <button onClick={() => setShowAttach(false)} className="text-xs text-gray-400">Cancel</button>
            </div>
          )}
        </div>
      </div>

      {loading && <p className="text-sm text-gray-400 text-center py-6">Loading…</p>}

      {!loading && (
        <div className="space-y-5">
          {Object.entries(byDate).map(([date, items]) => (
            <div key={date}>
              <div className="flex items-center gap-2 mb-3">
                <div className="h-px flex-1 bg-gray-200" />
                <span className="text-xs text-gray-400 font-medium px-2">{date}</span>
                <div className="h-px flex-1 bg-gray-200" />
              </div>
              <div className="space-y-2.5">
                {items.map(a => (
                  <ActivityCard key={a.activity_id} activity={a} currentUser={currentUser} onUpdate={load} />
                ))}
              </div>
            </div>
          ))}
          {activities.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-8">
              No activity yet. Be the first to comment.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
