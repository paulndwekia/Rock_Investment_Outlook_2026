"use client";

import { useEffect, useState } from "react";
import { Download, Smartphone, X } from "lucide-react";

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform?: string }>;
};

export default function InstallPwaButton() {
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => {
    if (window.matchMedia("(display-mode: standalone)").matches) {
      setInstalled(true);
    }

    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch(() => {
        // The website remains usable if offline support is unavailable.
      });
    }

    const handleBeforeInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };

    const handleInstalled = () => {
      setInstalled(true);
      setInstallPrompt(null);
      setHelpOpen(false);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);
    window.addEventListener("appinstalled", handleInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  async function handleInstall() {
    if (!installPrompt) {
      setHelpOpen((current) => !current);
      return;
    }

    try {
      await installPrompt.prompt();
      const choice = await installPrompt.userChoice;
      if (choice.outcome === "accepted") {
        setInstalled(true);
      }
    } finally {
      setInstallPrompt(null);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => void handleInstall()}
        disabled={installed}
        aria-expanded={helpOpen}
        aria-label={installed ? "App installed" : "Install Kenya Investment Intelligence"}
        className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#D9D2C4] bg-[#F8F6F0] px-3 text-xs font-semibold text-[#6E5934] transition hover:border-[#B89552] hover:bg-white disabled:cursor-default disabled:opacity-70"
      >
        {installed ? <Smartphone size={14} /> : <Download size={14} />}
        <span className="hidden sm:inline">{installed ? "Installed" : "Install"}</span>
      </button>

      {helpOpen && !installed && (
        <div className="absolute right-0 top-11 z-50 w-[min(290px,calc(100vw-2rem))] rounded-xl border border-[#E7E3DA] bg-white p-4 text-left shadow-xl">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-[#263139]">Add to your phone</p>
              <p className="mt-1 text-xs leading-5 text-[#858B86]">Install the research dashboard from your browser menu.</p>
            </div>
            <button onClick={() => setHelpOpen(false)} aria-label="Close installation help" className="rounded-md p-1 text-[#858B86] hover:bg-[#F4F2EC]"><X size={15} /></button>
          </div>
          <div className="mt-3 space-y-3 text-xs leading-5 text-[#56615E]">
            <div><p className="font-semibold text-[#34403C]">Android · Chrome</p><p>Open the ⋮ menu, then choose “Install app” or “Add to Home screen”.</p></div>
            <div><p className="font-semibold text-[#34403C]">iPhone · Safari</p><p>Tap Share, then “Add to Home Screen”.</p></div>
          </div>
        </div>
      )}
    </div>
  );
}
