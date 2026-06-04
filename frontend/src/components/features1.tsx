import { BarChart3, Bookmark, Search, Share2, Zap } from "lucide-react";

const features = [
  {
    title: "Pencarian Lebih Relevan",
    description:
      "Algoritma yang membantu menemukan artikel paling relevan.",
    icon: Search,
    color: "bg-indigo-100 text-indigo-600",
  },
  {
    title: "Relasi Penelitian Terlihat",
    description:
      "Citation Network yang memvisualisasikan hubungan antar penelitian.",
    icon: Share2,
    color: "bg-teal-100 text-teal-600",
  },
  {
    title: "Analisis Lebih Cepat",
    description:
      "Filter dan visualisasi membantu memahami tren penelitian.",
    icon: Zap,
    color: "bg-orange-100 text-orange-500",
  },
  {
    title: "Kelola Referensi Mudah",
    description:
      "Simpan artikel favorit dan akses kembali kapan saja dengan mudah.",
    icon: Bookmark,
    color: "bg-sky-100 text-sky-600",
  },
  {
    title: "Dukung Keputusan Riset",
    description:
      "Temukan topik potensial dan paper penting untuk penelitian.",
    icon: BarChart3,
    color: "bg-violet-100 text-violet-600",
  },
];

export default function Features() {
  return (
    <section id="fitur" className="bg-white px-6 py-8">
      <div className="mx-auto max-w-7xl rounded-3xl bg-slate-50 px-6 py-10 shadow-sm">
        <h2 className="text-center text-2xl font-extrabold text-slate-950">
          Kenapa Menggunakan PaperCi?
        </h2>
        <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {features.map(({ title, description, icon: Icon, color }) => (
            <div
              key={title}
              className="rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm transition hover:-translate-y-1 hover:shadow-md"
            >
              <div className={`mx-auto flex h-16 w-16 items-center justify-center rounded-full ${color}`}>
                <Icon className="h-8 w-8" />
              </div>
              <h3 className="mt-5 font-extrabold text-slate-950">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
