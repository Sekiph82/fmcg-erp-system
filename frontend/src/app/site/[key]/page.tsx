import { redirect } from "next/navigation";

// /site/<key> → the site's home in English; the page endpoint falls back to the site's default language.
export default async function SiteRoot({ params }: { params: Promise<{ key: string }> }) {
  const { key } = await params;
  redirect(`/site/${key}/en`);
}
