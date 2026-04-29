import { Toaster } from "sonner";
import { ChatLayout } from "@/components/ChatLayout";

export default function Home() {
  return (
    <>
      <ChatLayout />
      <Toaster position="top-right" richColors />
    </>
  );
}
