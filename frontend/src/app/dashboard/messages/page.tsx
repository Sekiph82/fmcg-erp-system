"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { messagingApi, Channel, Message, timeAgo } from "@/lib/messaging";
import { Button } from "@/components/ui/Button";

const MODULE_COLORS: Record<string, string> = {
  sales:       "bg-blue-100 text-blue-700",
  production:  "bg-purple-100 text-purple-700",
  quality:     "bg-green-100 text-green-700",
  finance:     "bg-amber-100 text-amber-700",
  procurement: "bg-orange-100 text-orange-700",
};

function Avatar({ initials, size = "md" }: { initials?: string | null; size?: "sm" | "md" }) {
  const sz = size === "sm" ? "w-6 h-6 text-xs" : "w-8 h-8 text-sm";
  return (
    <div className={`${sz} rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold shrink-0`}>
      {initials ?? "?"}
    </div>
  );
}

function MessageBubble({
  msg, onReply, onEdit, onDelete,
}: {
  msg: Message;
  onReply: (m: Message) => void;
  onEdit: (m: Message) => void;
  onDelete: (m: Message) => void;
}) {
  const [hover, setHover] = useState(false);

  return (
    <div
      className="flex items-start gap-3 group px-4 py-1.5 hover:bg-gray-50 rounded"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <Avatar initials={msg.sender_initials} />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold text-gray-900">{msg.sender_name ?? "Unknown"}</span>
          <span className="text-xs text-gray-400">{timeAgo(msg.created_at)}</span>
          {msg.is_edited && <span className="text-xs text-gray-400 italic">(edited)</span>}
        </div>
        {msg.is_deleted ? (
          <p className="text-sm text-gray-400 italic">[deleted]</p>
        ) : (
          <>
            <p className="text-sm text-gray-800 whitespace-pre-wrap break-words">{msg.body}</p>
            {msg.link_ref && (
              <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded ${MODULE_COLORS[msg.link_module ?? ""] ?? "bg-gray-100 text-gray-600"}`}>
                🔗 {msg.link_type} · {msg.link_ref}
              </span>
            )}
            {msg.reply_count > 0 && (
              <button
                className="mt-1 text-xs text-indigo-600 hover:underline"
                onClick={() => onReply(msg)}
              >
                {msg.reply_count} {msg.reply_count === 1 ? "reply" : "replies"}
              </button>
            )}
          </>
        )}
      </div>
      {hover && !msg.is_deleted && (
        <div className="flex gap-1 shrink-0">
          <button className="text-xs text-gray-400 hover:text-gray-700 px-1.5 py-0.5 rounded hover:bg-gray-200" onClick={() => onReply(msg)}>Reply</button>
          <button className="text-xs text-gray-400 hover:text-gray-700 px-1.5 py-0.5 rounded hover:bg-gray-200" onClick={() => onEdit(msg)}>Edit</button>
          <button className="text-xs text-red-400 hover:text-red-600 px-1.5 py-0.5 rounded hover:bg-red-50" onClick={() => onDelete(msg)}>Delete</button>
        </div>
      )}
    </div>
  );
}

export default function MessagesPage() {
  const qc = useQueryClient();
  const [activeChannel, setActiveChannel] = useState<Channel | null>(null);
  const [compose, setCompose] = useState("");
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [editMsg, setEditMsg] = useState<Message | null>(null);
  const [threadMsg, setThreadMsg] = useState<Message | null>(null);
  const [searchQ, setSearchQ] = useState("");
  const [showNewChannel, setShowNewChannel] = useState(false);
  const [newChannelName, setNewChannelName] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: channels = [], isLoading: chLoading } = useQuery({
    queryKey: ["channels"],
    queryFn: () => messagingApi.listChannels(),
    refetchInterval: 10_000,
  });

  const { data: page, isLoading: msgsLoading } = useQuery({
    queryKey: ["messages", activeChannel?.id],
    queryFn: () => messagingApi.getMessages(activeChannel!.id, { limit: 50 }),
    enabled: !!activeChannel,
    refetchInterval: 5_000,
  });

  const { data: thread = [] } = useQuery({
    queryKey: ["thread", threadMsg?.id],
    queryFn: () => messagingApi.getThread(activeChannel!.id, threadMsg!.id),
    enabled: !!threadMsg && !!activeChannel,
    refetchInterval: 5_000,
  });

  const { data: searchResults = [] } = useQuery({
    queryKey: ["msg-search", searchQ, activeChannel?.id],
    queryFn: () => messagingApi.search(searchQ, activeChannel?.id),
    enabled: searchQ.length >= 2,
  });

  const postMessage = useMutation({
    mutationFn: () => messagingApi.postMessage(activeChannel!.id, {
      body: editMsg ? editMsg.body : compose,
      parent_id: replyTo?.id,
    }),
    onSuccess: () => {
      setCompose(""); setReplyTo(null);
      qc.invalidateQueries({ queryKey: ["messages"] });
    },
  });

  const editMutation = useMutation({
    mutationFn: () => messagingApi.editMessage(editMsg!.id, compose),
    onSuccess: () => { setEditMsg(null); setCompose(""); qc.invalidateQueries({ queryKey: ["messages"] }); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => messagingApi.deleteMessage(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["messages"] }),
  });

  const createChannel = useMutation({
    mutationFn: () => messagingApi.createChannel({ name: newChannelName }),
    onSuccess: (ch) => {
      qc.invalidateQueries({ queryKey: ["channels"] });
      setActiveChannel(ch);
      setShowNewChannel(false);
      setNewChannelName("");
    },
  });

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [page?.messages.length]);

  const messages = page?.messages ?? [];

  function handleSend() {
    if (!compose.trim() || !activeChannel) return;
    if (editMsg) {
      editMutation.mutate();
    } else {
      postMessage.mutate();
    }
  }

  return (
    <div className="h-[calc(100vh-120px)] flex rounded-xl border bg-white overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 border-r flex flex-col shrink-0">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <span className="font-semibold text-gray-800">Messages</span>
          <button className="text-indigo-600 hover:underline text-xs" onClick={() => setShowNewChannel(true)}>+ New</button>
        </div>

        {/* Search */}
        <div className="px-3 py-2 border-b">
          <input
            className="w-full border rounded px-2 py-1.5 text-xs"
            placeholder="Search messages…"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
          />
        </div>

        {/* Channel list */}
        <div className="flex-1 overflow-y-auto py-2">
          {chLoading ? (
            <p className="px-4 py-3 text-xs text-gray-400">Loading…</p>
          ) : channels.length === 0 ? (
            <p className="px-4 py-3 text-xs text-gray-400">No channels yet</p>
          ) : (
            channels.map((ch) => (
              <button
                key={ch.id}
                className={`w-full text-left px-4 py-2 hover:bg-gray-50 flex items-center gap-2 ${activeChannel?.id === ch.id ? "bg-indigo-50 text-indigo-700" : "text-gray-700"}`}
                onClick={() => { setActiveChannel(ch); setThreadMsg(null); setSearchQ(""); }}
              >
                <span className="text-gray-400">{ch.channel_type === "DIRECT" ? "◉" : "#"}</span>
                <span className="flex-1 text-sm truncate">{ch.name}</span>
                {ch.unread_count > 0 && (
                  <span className="bg-indigo-600 text-white text-xs rounded-full px-1.5 py-0.5 shrink-0">
                    {ch.unread_count > 99 ? "99+" : ch.unread_count}
                  </span>
                )}
              </button>
            ))
          )}
        </div>

        {showNewChannel && (
          <div className="px-3 py-3 border-t space-y-2">
            <input
              className="w-full border rounded px-2 py-1.5 text-xs"
              placeholder="Channel name…"
              value={newChannelName}
              onChange={(e) => setNewChannelName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && newChannelName.trim() && createChannel.mutate()}
              autoFocus
            />
            <div className="flex gap-1">
              <button className="flex-1 text-xs bg-indigo-600 text-white rounded py-1 hover:bg-indigo-700" onClick={() => newChannelName.trim() && createChannel.mutate()}>Create</button>
              <button className="flex-1 text-xs border rounded py-1" onClick={() => setShowNewChannel(false)}>Cancel</button>
            </div>
          </div>
        )}
      </div>

      {/* Main chat area */}
      {!activeChannel ? (
        <div className="flex-1 flex items-center justify-center text-gray-400">
          <div className="text-center">
            <p className="text-2xl mb-2">💬</p>
            <p className="text-sm">Select a channel to start messaging</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <div className="px-5 py-3 border-b flex items-center justify-between">
            <div>
              <span className="font-semibold text-gray-900">
                {activeChannel.channel_type === "DIRECT" ? "◉" : "#"} {activeChannel.name}
              </span>
              {activeChannel.description && (
                <p className="text-xs text-gray-500">{activeChannel.description}</p>
              )}
            </div>
            <span className="text-xs text-gray-400">{activeChannel.member_count} members</span>
          </div>

          {/* Search results overlay */}
          {searchQ.length >= 2 ? (
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
              <p className="text-xs text-gray-500 font-medium">Search results for &quot;{searchQ}&quot;</p>
              {searchResults.length === 0 ? (
                <p className="text-sm text-gray-400">No results</p>
              ) : searchResults.map((m) => (
                <div key={m.id} className="border rounded p-3 text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-gray-800">{m.sender_name}</span>
                    <span className="text-xs text-gray-400">{timeAgo(m.created_at)}</span>
                  </div>
                  <p className="text-gray-700">{m.body}</p>
                </div>
              ))}
            </div>
          ) : threadMsg ? (
            /* Thread view */
            <div className="flex-1 overflow-y-auto">
              <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Thread</span>
                <button className="text-xs text-gray-500 hover:text-gray-700" onClick={() => setThreadMsg(null)}>← Back</button>
              </div>
              <div className="px-4 py-2 border-b bg-white">
                <MessageBubble msg={threadMsg} onReply={() => {}} onEdit={() => {}} onDelete={() => {}} />
              </div>
              <div className="divide-y">
                {thread.map((m) => (
                  <MessageBubble key={m.id} msg={m}
                    onReply={() => {}}
                    onEdit={(msg) => { setEditMsg(msg); setCompose(msg.body); }}
                    onDelete={(msg) => deleteMutation.mutate(msg.id)}
                  />
                ))}
              </div>
              <div ref={bottomRef} />
            </div>
          ) : (
            /* Main messages */
            <div className="flex-1 overflow-y-auto">
              {msgsLoading ? (
                <p className="px-5 py-8 text-center text-gray-400">Loading…</p>
              ) : messages.length === 0 ? (
                <p className="px-5 py-12 text-center text-gray-400">No messages yet — be the first!</p>
              ) : (
                <div className="py-2">
                  {messages.map((m) => (
                    <MessageBubble key={m.id} msg={m}
                      onReply={(msg) => { setReplyTo(msg); setThreadMsg(msg); }}
                      onEdit={(msg) => { setEditMsg(msg); setCompose(msg.body); }}
                      onDelete={(msg) => deleteMutation.mutate(msg.id)}
                    />
                  ))}
                  <div ref={bottomRef} />
                </div>
              )}
            </div>
          )}

          {/* Compose */}
          <div className="border-t p-3 space-y-2">
            {replyTo && !threadMsg && (
              <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 rounded px-3 py-1.5">
                <span>↩ Replying to {replyTo.sender_name}</span>
                <button className="ml-auto text-gray-400 hover:text-gray-700" onClick={() => setReplyTo(null)}>✕</button>
              </div>
            )}
            {editMsg && (
              <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 rounded px-3 py-1.5">
                <span>✏ Editing message</span>
                <button className="ml-auto text-gray-400 hover:text-gray-700" onClick={() => { setEditMsg(null); setCompose(""); }}>✕</button>
              </div>
            )}
            <div className="flex items-end gap-2">
              <textarea
                className="flex-1 border rounded px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300"
                rows={2}
                placeholder={`Message #${activeChannel.name}… (use @username to mention)`}
                value={compose}
                onChange={(e) => setCompose(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
              />
              <Button
                onClick={handleSend}
                loading={postMessage.isPending || editMutation.isPending}
                disabled={!compose.trim()}
                className="shrink-0"
              >
                {editMsg ? "Update" : "Send"}
              </Button>
            </div>
            <p className="text-xs text-gray-400">Enter to send · Shift+Enter for newline</p>
          </div>
        </div>
      )}
    </div>
  );
}
