import { useEffect, useRef, useState } from "react";
import {
  Bot,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Database,
  FileSearch,
  FileText,
  Filter,
  GitCompare,
  Layers,
  Loader2,
  Network,
  Search,
  SearchX,
  Sparkles,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { SearchProgressEvent } from "@/api/api";
import {
  useDotTicker,
  useMicroTicker,
  useScriptedStages,
  useTypingText,
  type ScriptedResultStatus,
  type ScriptedStageStatus,
  type ScriptedStageView,
} from "./search-progress-animation";

// Ikon untuk tiap tahap (urutan mengikuti SCRIPTED_STAGE_DEFS).
const stageIcons = [
  Search,
  Database,
  FileText,
  Sparkles,
  Layers,
  GitCompare,
  GitCompare,
  Filter,
  Network,
  ClipboardCheck,
];

// Catatan kecil generik yang berputar selama sebuah tahap berjalan, agar
// terasa lebih "hidup" & detail. Tidak mengklaim proses spesifik apa pun.
const MICRO_PHRASES = [
  "Menyusun potongan data...",
  "Memeriksa kecocokan istilah...",
  "Menyaring hasil yang relevan...",
  "Merapikan urutan data...",
  "Melakukan pengecekan tambahan...",
  "Menyiapkan ringkasan proses...",
];

type TransitionKind = "found" | "empty";

interface RequestForm {
  nama: string;
  email: string;
  kataKunci: string;
  judulArtikel: string;
  keterangan: string;
}

/**
 * Form "Request Artikel" yang tampil langsung di dalam popup scraper saat
 * artikel tidak ditemukan (dipindahkan dari halaman pencarian ke sini,
 * logikanya sama: POST ke /api/request-article).
 */
function RequestArticleForm({
  query,
  onSubmitted,
}: {
  query: string;
  onSubmitted: () => void;
}) {
  const [form, setForm] = useState<RequestForm>({
    nama: "",
    email: "",
    kataKunci: query || "",
    judulArtikel: "",
    keterangan: "",
  });
  const [loading, setLoading] = useState(false);
  const [notif, setNotif] = useState("");
  const [notifType, setNotifType] = useState<"success" | "error">("success");

  const handleChange = (key: keyof RequestForm, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setNotif("");

      const res = await fetch("http://127.0.0.1:5000/api/request-article", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      const data = await res.json();

      if (!res.ok || data?.status === "error") {
        setNotifType("error");
        setNotif(data?.message || "Gagal mengirim permintaan.");
        return;
      }

      setNotifType(data?.email_sent === false ? "error" : "success");
      setNotif(data?.message || "Permintaan berhasil dikirim.");

      window.setTimeout(() => {
        onSubmitted();
      }, 1500);
    } catch (error: any) {
      setNotifType("error");
      setNotif(error?.message || "Gagal mengirim permintaan.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-md text-left">
      {notif && (
        <div
          className={cn(
            "mb-4 rounded-lg px-3 py-2 text-center text-sm font-medium",
            notifType === "success" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700",
          )}
        >
          {notif}
        </div>
      )}

      <div className="space-y-3">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm">Nama</label>
          <Input
            value={form.nama}
            onChange={(e) => handleChange("nama", e.target.value)}
            placeholder="Nama lengkap"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm">Email</label>
          <Input
            type="email"
            value={form.email}
            onChange={(e) => handleChange("email", e.target.value)}
            placeholder="email@contoh.com"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm">Kata Kunci Pencarian</label>
          <Input
            value={form.kataKunci}
            onChange={(e) => handleChange("kataKunci", e.target.value)}
            placeholder="Contoh: web accessibility"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm">Judul Artikel (Opsional)</label>
          <Input
            value={form.judulArtikel}
            onChange={(e) => handleChange("judulArtikel", e.target.value)}
            placeholder="Jika ada judul spesifik"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm">Keterangan Tambahan (Opsional)</label>
          <textarea
            value={form.keterangan}
            onChange={(e) => handleChange("keterangan", e.target.value)}
            placeholder="Tambahkan detail permintaan..."
            className="min-h-[90px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>

        <div className="flex justify-center pt-1">
          <Button
            onClick={handleSubmit}
            className="px-10"
            disabled={loading || !form.nama.trim() || !form.email.trim() || !form.kataKunci.trim()}
          >
            {loading ? "Mengirim..." : "Kirim Permintaan"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function statusLabel(status: ScriptedStageStatus) {
  if (status === "done") return "Selesai";
  if (status === "running") return "Berjalan...";
  return "Menunggu";
}

function statusClass(status: ScriptedStageStatus) {
  if (status === "done") return "text-emerald-600";
  if (status === "running") return "text-blue-600";
  return "text-slate-400";
}

/** Tiga titik berjalan ala "thinking indicator" (ChatGPT/Claude style). */
function ThinkingDots({ className }: { className?: string }) {
  const tick = useDotTicker(3, 380);
  return (
    <span className={cn("inline-flex items-center gap-0.5", className)}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className={cn(
            "h-1 w-1 rounded-full bg-current transition-opacity duration-150",
            i <= tick ? "opacity-100" : "opacity-25",
          )}
        />
      ))}
    </span>
  );
}

/** Teks yang muncul huruf demi huruf, retype tiap kali `text` berubah. */
function TypingText({
  text,
  speed = 22,
  className,
  cursor = false,
}: {
  text: string;
  speed?: number;
  className?: string;
  cursor?: boolean;
}) {
  const shown = useTypingText(text, speed);
  const isTyping = shown.length < text.length;

  return (
    <span className={className}>
      {shown}
      {cursor && (
        <span
          className={cn(
            "ml-0.5 inline-block h-3 w-[2px] -mb-0.5 bg-current align-middle",
            isTyping ? "animate-pulse opacity-80" : "opacity-0",
          )}
        />
      )}
    </span>
  );
}

function StepMarker({ status }: { status: ScriptedStageStatus }) {
  if (status === "done") {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white shadow-sm shadow-emerald-200 transition-all duration-500">
        <Check className="h-3.5 w-3.5" />
      </span>
    );
  }

  return (
    <span
      className={cn(
        "h-5 w-5 rounded-full border-2 bg-white transition-all duration-500",
        status === "running" ? "border-blue-600 bg-blue-600 ring-4 ring-blue-100" : "border-slate-300",
      )}
    />
  );
}

function ProcessStep({
  stage,
  index,
}: {
  stage: ScriptedStageView;
  index: number;
}) {
  const Icon = stageIcons[index] || FileText;
  const isRunning = stage.status === "running";
  const microDetail = useMicroTicker(isRunning, MICRO_PHRASES, 1700);

  return (
    <div
      className={cn(
        "grid grid-cols-[2rem_1fr] gap-3 border-b border-slate-100 px-3 py-3 transition-colors duration-500 last:border-b-0 md:grid-cols-[2rem_1fr_auto]",
        stage.status === "running" && "bg-blue-50/40",
      )}
    >
      <div
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-lg transition-all duration-500",
          stage.status === "done" && "bg-emerald-50 text-emerald-600",
          stage.status === "running" && "bg-blue-100 text-blue-600 animate-[sp-pulse-soft_1.6s_ease-in-out_infinite]",
          stage.status === "waiting" && "bg-slate-100 text-slate-400",
        )}
      >
        <Icon className="h-5 w-5" />
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <h3 className="text-sm font-semibold text-slate-900">
            {index + 1}. {stage.title}
          </h3>
          {isRunning && <ThinkingDots className="text-blue-500" />}
          <span className={cn("text-xs font-medium md:hidden", statusClass(stage.status))}>
            {statusLabel(stage.status)}
          </span>
        </div>
        <p className="mt-1 text-sm leading-snug text-slate-500">{stage.description}</p>

        {isRunning && (
          <div className="mt-3 rounded-md border border-blue-100 bg-white px-3 py-2 text-xs text-slate-600 shadow-sm">
            <p className="italic text-slate-400">
              <TypingText key={`${stage.key}-micro-${microDetail}`} text={microDetail} speed={22} />
            </p>
          </div>
        )}
      </div>

      <div className="hidden min-w-[6.5rem] text-right md:block">
        <p className={cn("text-sm font-medium transition-colors duration-500", statusClass(stage.status))}>
          {statusLabel(stage.status)}
        </p>
      </div>
    </div>
  );
}

/**
 * Layar transisi penutup, sengaja dibuat polos (tanpa kartu/kotak) supaya
 * perpindahan dari popup proses ke langkah berikutnya terasa mulus, baik
 * saat artikel ditemukan maupun saat tidak ada hasil yang cocok.
 */
function TransitionScreen({
  kind,
  query,
  showRequestForm,
  onOpenRequestForm,
  onRequestSubmitted,
}: {
  kind: TransitionKind;
  query: string;
  showRequestForm: boolean;
  onOpenRequestForm: () => void;
  onRequestSubmitted: () => void;
}) {
  if (kind === "empty") {
    if (showRequestForm) {
      return (
        <div className="px-6 py-8">
          <div className="mb-5 text-center">
            <p className="text-base font-semibold text-slate-700">Kirim Permintaan Artikel</p>
            <p className="mt-1 text-sm text-slate-500">
              Kata kunci "{query}" belum tersedia. Isi form berikut agar tim kami menambahkannya.
            </p>
          </div>
          <RequestArticleForm query={query} onSubmitted={onRequestSubmitted} />
        </div>
      );
    }

    return (
      <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
        <SearchX className="h-10 w-10 text-slate-300" />
        <div>
          <p className="text-base font-semibold text-slate-700">Artikel tidak ditemukan</p>
          <p className="mt-1 text-sm text-slate-500">
            Kata kunci "{query}" belum tersedia dalam sistem. Coba kata kunci lain, atau kirim
            permintaan kepada developer.
          </p>
        </div>
        <Button onClick={onOpenRequestForm} className="mt-2 px-8">
          Request
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-4 px-6 py-20 text-center">
      <div className="relative flex h-14 w-14 items-center justify-center">
        <Loader2 className="h-14 w-14 animate-spin text-blue-200" />
        <CheckCircle2 className="absolute h-7 w-7 text-emerald-500" />
      </div>
      <div>
        <p className="text-lg font-semibold text-slate-900">Artikel ditemukan!</p>
        <p className="mt-1 text-sm text-slate-500">Menyiapkan halaman hasil untuk Anda...</p>
      </div>
    </div>
  );
}


export function SearchProgressDialog({
  open,
  progress,
  query,
  category,
  onOpenChange,
  startedAt,
  onFinished,
}: {
  open: boolean;
  progress: SearchProgressEvent | null;
  query: string;
  category: string;
  onOpenChange: (open: boolean) => void;
  /** Timestamp (Date.now()) saat pencarian dimulai, dipakai untuk timeline tahapan. */
  startedAt?: number | null;
  /** Dipanggil setelah layar transisi penutup tampil sebentar. */
  onFinished?: () => void;
}) {
  const isComplete = progress?.status === "complete";
  const isActive = open && !!progress;
  const articleCount = Array.isArray(progress?.result?.articles) ? progress!.result!.articles.length : 0;

  // Status hasil dipakai untuk menentukan kapan animasi harus dihentikan
  // lebih awal (di tahap scraping) saat artikel tidak ditemukan.
  const resultStatus: ScriptedResultStatus = !isComplete
    ? "pending"
    : articleCount > 0
    ? "found"
    : "empty";

  const { stages, percent, isFinished, isEmptyHalted } = useScriptedStages(
    isComplete,
    isActive,
    startedAt ?? null,
    resultStatus,
  );

  const [transitionKind, setTransitionKind] = useState<TransitionKind | null>(null);
  const [showRequestForm, setShowRequestForm] = useState(false);
  const firedRef = useRef(false);

  useEffect(() => {
    if (!isActive) {
      firedRef.current = false;
      setTransitionKind(null);
      setShowRequestForm(false);
      return;
    }
    // Untuk hasil "found": tunggu seluruh 10 tahap selesai + backend complete.
    // Untuk hasil "empty": animasi dihentikan lebih awal tepat di tahap
    // scraping ("dataset"), lalu langsung tampilkan popup "tidak ditemukan".
    const readyToReveal = isFinished || isEmptyHalted;
    if (readyToReveal && !firedRef.current) {
      firedRef.current = true;
      const kind: TransitionKind = resultStatus === "found" ? "found" : "empty";

      const revealTimer = window.setTimeout(() => setTransitionKind(kind), 300);
      return () => window.clearTimeout(revealTimer);
    }
  }, [isFinished, isEmptyHalted, isActive, resultStatus]);

  // Hanya kasus "found" yang otomatis lanjut (navigasi ke hasil). Kasus
  // "empty" dibiarkan terbuka supaya pengguna bisa memakai tombol Request
  // tanpa didahului auto-close.
  useEffect(() => {
    if (transitionKind !== "found") return;
    const navTimer = window.setTimeout(() => {
      onFinished?.();
    }, 5000);
    return () => window.clearTimeout(navTimer);
  }, [transitionKind, onFinished]);

  // Selalu tampilkan teks statis ini di bawah judul (tidak lagi memakai
  // pesan dinamis dari backend, misal "Proses selesai. 10 artikel siap
  // ditampilkan.").
  const activeMessage = "Sedang Menyiapkan Hasil Pencarian";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          "max-h-[92vh] max-w-6xl overflow-hidden rounded-xl p-0",
          // Override default slide animation: buka/tutup terasa seperti "pop"
          // (muncul & menghilang di tempat, cuma fade + zoom) bukan geser ke pojok.
          "data-[state=open]:slide-in-from-left-0 data-[state=open]:slide-in-from-top-0",
          "data-[state=closed]:slide-out-to-left-0 data-[state=closed]:slide-out-to-top-0",
          "data-[state=closed]:duration-300 data-[state=closed]:ease-out",
        )}
      >
        <style>{`
          @keyframes sp-pulse-soft {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.72; transform: scale(1.08); }
          }
          @keyframes sp-shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(220%); }
          }
          @keyframes sp-fade-in {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
          }
          .sp-fade-in { animation: sp-fade-in 400ms ease-out both; }
          .sp-progress-shimmer::after {
            content: "";
            position: absolute;
            inset: 0;
            width: 40%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.55), transparent);
            animation: sp-shimmer 1.6s ease-in-out infinite;
          }
        `}</style>

        <DialogHeader className="border-b px-5 py-4 pr-12">
          <div className="flex items-center gap-3">
            <DialogTitle className="flex items-center gap-3 text-xl font-semibold">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                <FileSearch className="h-5 w-5" />
              </span>
              Sedang Menyiapkan Hasil Pencarian
            </DialogTitle>
          </div>

          {!transitionKind && (
            <div className="mt-4 inline-flex max-w-full flex-wrap items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm text-slate-700">
              <Search className="h-4 w-4 text-blue-600" />
              <span className="font-semibold">Keyword:</span>
              <span>"{query}"</span>
              <span className="text-slate-300">-</span>
              <span className="font-semibold">Sumber Pencarian:</span>
              <span>Google Scholar</span>
            </div>
          )}
        </DialogHeader>

        {transitionKind ? (
          <div key="transition" className="sp-fade-in">
            <TransitionScreen
              kind={transitionKind}
              query={query}
              showRequestForm={showRequestForm}
              onOpenRequestForm={() => setShowRequestForm(true)}
              onRequestSubmitted={() => {
                setShowRequestForm(false);
                onOpenChange(false);
              }}
            />
          </div>
        ) : (
          <div key="stages" className="sp-fade-in max-h-[calc(92vh-8.5rem)] overflow-y-auto">
            <div className="border-b px-5 py-5">
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    "flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-600",
                    !isComplete && "animate-[sp-pulse-soft_1.8s_ease-in-out_infinite]",
                  )}
                >
                  <Bot className="h-7 w-7" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="flex items-center gap-2 font-semibold text-slate-950">
                        Saya sedang mencari artikel untuk Anda
                        {!isComplete && <ThinkingDots className="text-slate-500" />}
                      </p>
                      <p className="mt-1 min-h-[1.25rem] text-sm text-slate-500">
                        <TypingText key={activeMessage} text={activeMessage} speed={24} cursor={!isComplete} />
                      </p>
                    </div>
                  </div>

                  <div className="mt-5 flex items-center gap-3">
                    <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                      <div
                        className="sp-progress-shimmer relative h-full overflow-hidden rounded-full bg-gradient-to-r from-blue-500 to-blue-600 transition-[width] duration-300 ease-linear"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                    <span className="w-11 text-right text-sm font-semibold tabular-nums text-blue-600">
                      {percent}%
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4 px-5 py-5 lg:grid-cols-[3rem_1fr]">
              <div className="hidden flex-col items-center pt-6 lg:flex">
                {stages.map((stage, index) => (
                  <div key={stage.key} className="flex flex-col items-center">
                    <StepMarker status={stage.status} />
                    {index < stages.length - 1 && <span className="h-12 w-px bg-slate-200" />}
                  </div>
                ))}
              </div>

              <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                {stages.map((stage, index) => (
                  <ProcessStep key={stage.key} stage={stage} index={index} />
                ))}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
