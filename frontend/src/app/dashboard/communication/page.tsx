"use client";

import dynamic from "next/dynamic";
import { ModuleWorkspace } from "@/components/workspace";
import { tx } from "@/lib/i18n/core";

const ChatterPage       = dynamic(() => import("@/app/dashboard/chatter/page"),              { ssr: false });
const CalendarPage      = dynamic(() => import("@/app/dashboard/calendar/page"),             { ssr: false });
const MessagesPage      = dynamic(() => import("@/app/dashboard/messages/page"),             { ssr: false });
const EmailPage         = dynamic(() => import("@/app/dashboard/email/page"),                { ssr: false });
const WhatsAppPage      = dynamic(() => import("@/app/dashboard/whatsapp/page"),             { ssr: false });
const CallsPage         = dynamic(() => import("@/app/dashboard/calls/page"),                { ssr: false });
const MeetingsPage      = dynamic(() => import("@/app/dashboard/meetings/page"),             { ssr: false });
const NotifPage         = dynamic(() => import("@/app/dashboard/notification-center/page"), { ssr: false });

export default function CommunicationPage() {
  const tabs = [
    { key: "messages",      label: tx("Messages"),      permission: "hr.view",                content: <MessagesPage /> },
    { key: "chatter",       label: tx("Chatter"),       permission: "hr.view",                content: <ChatterPage /> },
    { key: "email",         label: tx("Email"),         permission: "integrations.view",       content: <EmailPage /> },
    { key: "whatsapp",      label: tx("WhatsApp"),      permission: "integrations.view",       content: <WhatsAppPage /> },
    { key: "calls",         label: tx("Calls"),         permission: "sales.view",              content: <CallsPage /> },
    { key: "meetings",      label: tx("Meetings"),      permission: "sales.view",              content: <MeetingsPage /> },
    { key: "calendar",      label: tx("Calendar"),      permission: "hr.view",                content: <CalendarPage /> },
    { key: "notifications", label: tx("Notifications"), permission: "notifications.view",      content: <NotifPage /> },
  ];

  return (
    <ModuleWorkspace
      title={tx("Communication")}
      description={tx("Messages, chatter, email, calls, calendar, notifications")}
      tabs={tabs}
      defaultTab="messages"
    />
  );
}
