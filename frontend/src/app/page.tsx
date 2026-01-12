import { redirect } from "next/navigation";

export default function Home() {
  // The app gate (/app layout) bounces to /login if unauthenticated.
  redirect("/app/workbench");
}
