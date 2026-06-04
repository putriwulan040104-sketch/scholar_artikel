import { BarChart3, Bookmark, FileText, Network, Search } from "lucide-react";

const demoSteps = [
  {
    title: "Masukkan Kata Kunci",
    description: "Ketik topik atau kata kunci penelitian yang ingin Anda cari.",
    icon: Search,
    accent: "bg-primary",
    preview: "search",
  },
  {
    title: "Lihat Hasil Pencarian",
    description: "Dapatkan daftar artikel yang paling relevan berdasarkan topik yang Anda cari.",
    icon: FileText,
    accent: "bg-indigo-600",
    preview: "results",
  },
  {
    title: "Eksplorasi Citation Network",
    description: "Klik artikel untuk melihat jaringan sitasi dan relasi antar penelitian.",
    icon: Network,
    accent: "bg-sky-600",
    preview: "graph",
  },
  {
    title: "Simpan ke Favorit",
    description: "Simpan artikel penting ke daftar favorit untuk akses cepat nanti.",
    icon: Bookmark,
    accent: "bg-orange-400",
    preview: "favorite",
  },
  {
    title: "Analisis Tren Penelitian",
    description: "Gunakan visualisasi data untuk menemukan tren penelitian.",
    icon: BarChart3,
    accent: "bg-teal-500",
    preview: "trend",
  },
];

function DemoPreview({
  preview,
  icon: Icon,
}: {
  preview: string;
  icon: typeof Search;
}) {
  if (preview === "search") {
    return (
      <div className="flex w-full items-center gap-2 rounded-lg border bg-white p-2">
        <span className="flex-1 rounded-md bg-slate-50 px-3 py-2 text-left text-[10px] text-slate-500">
          machine learning
        </span>
        <span className="rounded-md bg-primary p-2 text-primary-foreground">
          <Search className="h-4 w-4" />
        </span>
      </div>
    );
  }

  if (preview === "results") {
    return (
      <div className="grid w-full gap-2">
        {[0.85, 0.76, 0.72].map((score) => (
          <div
            key={score}
            className="flex items-center gap-2 rounded-md bg-white px-3 py-2"
          >
            <FileText className="h-4 w-4 text-primary" />
            <span className="h-2 flex-1 rounded-full bg-slate-200" />
            <span className="text-[10px] font-semibold text-primary">
              {score}
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (preview === "graph") return <MiniGraph />;

  if (preview === "favorite") {
    return (
      <div className="relative flex h-full w-full items-center justify-center">
        <div className="w-full rounded-xl bg-white p-4 shadow-sm">
          <div className="mb-3 h-3 w-3/4 rounded-full bg-slate-200" />
          <div className="mb-2 h-2 w-2/3 rounded-full bg-slate-200" />
          <div className="h-2 w-1/2 rounded-full bg-slate-200" />
        </div>
        <Bookmark className="absolute right-7 top-5 h-8 w-8 fill-primary text-primary" />
      </div>
    );
  }

  if (preview === "trend") {
    return (
      <div className="flex h-full w-full items-end justify-center gap-3 rounded-xl bg-white p-5 shadow-sm">
        {[36, 54, 72, 92].map((height) => (
          <div key={height} className="flex flex-col items-center gap-2">
            <span
              className="w-5 rounded-t-md bg-primary/80"
              style={{ height }}
            />
            <span className="h-1.5 w-5 rounded-full bg-slate-200" />
          </div>
        ))}
        <svg className="absolute h-20 w-28" viewBox="0 0 112 80" fill="none">
          <path
            d="M8 56L32 38L56 44L86 18L104 23"
            stroke="#6366f1"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    );
  }

  return <Icon className="h-12 w-12" />;
}

function MiniGraph() {
  const points = [
    [50, 50, "bg-primary"],
    [25, 28, "bg-teal-500"],
    [72, 25, "bg-indigo-500"],
    [78, 68, "bg-orange-400"],
    [30, 72, "bg-sky-500"],
  ];

  return (
    <div className="relative mx-auto h-24 w-full max-w-[170px]">
      <svg className="absolute inset-0 h-full w-full">
        <path
          d="M85 48 L42 27 M85 48 L122 24 M85 48 L132 65 M85 48 L50 70"
          stroke="#93c5fd"
          strokeWidth="2"
          fill="none"
        />
      </svg>
      {points.map(([left, top, color], index) => (
        <span
          key={`${left}-${top}`}
          className={`absolute flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full ${color} text-[10px] font-bold text-white shadow ring-4 ring-white`}
          style={{ left: `${left}%`, top: `${top}%` }}
        >
          {index + 1}
        </span>
      ))}
    </div>
  );
}

export default function AlurKerja() {
  return (
    <section id="demo" className="bg-white px-6 py-8">
      <div className="mx-auto max-w-7xl rounded-3xl bg-slate-50 px-6 py-10">
        <h2 className="text-center text-2xl font-extrabold text-slate-950">
          Cara Penggunaan PaperCi
        </h2>

        <div className="mt-10 grid gap-6 md:grid-cols-2 lg:grid-cols-5">
          {demoSteps.map(({ title, description, icon: Icon, accent, preview }, index) => (
            <div key={title} className="relative text-center">
              <div
                className={`mx-auto flex h-11 w-11 items-center justify-center rounded-full ${accent} text-lg font-extrabold text-white shadow-lg`}
              >
                {index + 1}
              </div>
              <div className="mt-4 flex h-36 items-center justify-center rounded-xl border border-slate-200 bg-white p-4 text-primary shadow-sm">
                <DemoPreview preview={preview} icon={Icon} />
              </div>
              <h3 className="mt-4 font-extrabold text-slate-950">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
