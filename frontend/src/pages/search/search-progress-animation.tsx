import { useEffect, useRef, useState } from "react";

/* =========================================================================
 * TAHAPAN TERJADWAL (nama ramah-pengguna, durasi realistis per tahap)
 * -------------------------------------------------------------------------
 * 10 tahap tetap dengan rentang durasi acak (dalam ms). Tahap sebelum
 * terakhir berjalan murni berdasarkan waktu (tidak menunggu backend). Tahap terakhir
 * ("Menyusun Hasil Akhir") punya durasi MINIMUM saja -- ia hanya boleh
 * benar-benar "selesai" kalau backend sudah mengirim status "complete".
 * Selama menunggu backend, progress bergerak sangat pelan (mendekati batas
 * atas tapi tidak pernah menyentuhnya) supaya tidak pernah "berbohong"
 * bahwa proses sudah selesai padahal belum.
 *
 * Persentase keseluruhan mengikuti pola:
 *   0–20%   -> cepat
 *   20–60%  -> normal, dengan jeda singkat di setiap pergantian tahap
 *   60–85%  -> melambat
 *   85–90%  -> menyusun jaringan relasi
 *   90–95%  -> sangat lambat (menunggu backend)
 *   100%    -> hanya saat backend benar-benar mengirim status "complete"
 * ====================================================================== */

export interface ScriptedStageDef {
  key: string;
  title: string;
  description: string;
  minMs: number;
  maxMs: number;
  percentStart: number;
  percentEnd: number;
  /** Sedikit jeda "diam" di awal tahap ini untuk kesan alami (band 20-60%). */
  pause?: boolean;
}

// Total waktu skrip: 60 detik, dibagi ke 10 tahap secara proporsional
// mengikuti target band persentase di bawah (lihat komentar atas file).
// Tiap sesi durasinya diacak +-15% dari basis ini supaya terasa alami
// dan tidak identik setiap pencarian.
export const SCRIPTED_TOTAL_MS = 60000;

function jitterRange(baseMs: number, spread = 0.15): [number, number] {
  return [Math.round(baseMs * (1 - spread)), Math.round(baseMs * (1 + spread))];
}

const [startMin, startMax] = jitterRange(0.08 * SCRIPTED_TOTAL_MS);
const [datasetMin, datasetMax] = jitterRange(0.12 * SCRIPTED_TOTAL_MS);
const [articleInfoMin, articleInfoMax] = jitterRange(0.18 * SCRIPTED_TOTAL_MS);
const [cleaningMin, cleaningMax] = jitterRange(0.09 * SCRIPTED_TOTAL_MS);
const [keywordMin, keywordMax] = jitterRange(0.09 * SCRIPTED_TOTAL_MS);
const [patternMin, patternMax] = jitterRange(0.07 * SCRIPTED_TOTAL_MS);
const [matchingMin, matchingMax] = jitterRange(0.12 * SCRIPTED_TOTAL_MS);
const [filteringMin, filteringMax] = jitterRange(0.07 * SCRIPTED_TOTAL_MS);
const [relationMin, relationMax] = jitterRange(0.08 * SCRIPTED_TOTAL_MS);
const [finalMin, finalMax] = jitterRange(0.1 * SCRIPTED_TOTAL_MS);

export const SCRIPTED_STAGE_DEFS: ScriptedStageDef[] = [
  {
    key: "start",
    title: "Memulai Pencarian",
    description: "Menyiapkan proses pencarian berdasarkan kata kunci Anda.",
    minMs: startMin,
    maxMs: startMax,
    percentStart: 0,
    percentEnd: 8,
  },
  {
    key: "dataset",
    title: "Menyiapkan Data Artikel",
    description: "Mengumpulkan data artikel yang tersedia di sistem.",
    minMs: datasetMin,
    maxMs: datasetMax,
    percentStart: 8,
    percentEnd: 20,
  },
  {
    key: "article-info",
    title: "Membaca Informasi Artikel",
    description: "Mengenali topik utama dan rujukan penting dari artikel.",
    minMs: articleInfoMin,
    maxMs: articleInfoMax,
    percentStart: 20,
    percentEnd: 40,
    pause: true,
  },
  {
    key: "cleaning",
    title: "Merapikan Kata Kunci",
    description: "Membersihkan dan menyusun kata kunci agar lebih akurat.",
    minMs: cleaningMin,
    maxMs: cleaningMax,
    percentStart: 40,
    percentEnd: 50,
    pause: true,
  },
  {
    key: "keyword-weight",
    title: "Menilai Kata Kunci Penting",
    description: "Menentukan seberapa penting tiap kata dalam artikel.",
    minMs: keywordMin,
    maxMs: keywordMax,
    percentStart: 50,
    percentEnd: 60,
    pause: true,
  },
  {
    key: "pattern",
    title: "Menyusun Pola Pencocokan",
    description: "Membentuk pola untuk membandingkan tiap artikel.",
    minMs: patternMin,
    maxMs: patternMax,
    percentStart: 60,
    percentEnd: 68,
  },
  {
    key: "matching",
    title: "Mencocokkan Artikel Relevan",
    description: "Membandingkan kemiripan tiap artikel dengan kata kunci Anda.",
    minMs: matchingMin,
    maxMs: matchingMax,
    percentStart: 68,
    percentEnd: 78,
  },
  {
    key: "filtering",
    title: "Menyaring Artikel",
    description: "Menerapkan filter dan memvalidasi hasil pencarian.",
    minMs: filteringMin,
    maxMs: filteringMax,
    percentStart: 78,
    percentEnd: 85,
  },
  {
    key: "relation-network",
    title: "Menyusun Jaringan Relasi",
    description: "Menghubungkan artikel berdasarkan kesamaan data.",
    minMs: relationMin,
    maxMs: relationMax,
    percentStart: 85,
    percentEnd: 90,
  },
  {
    key: "final",
    title: "Menyusun Hasil Akhir",
    description: "Mengurutkan dan menyiapkan hasil terbaik untuk Anda.",
    minMs: finalMin,
    maxMs: finalMax,
    percentStart: 90,
    percentEnd: 95,
  },
];

export type ScriptedStageStatus = "waiting" | "running" | "done";

export interface ScriptedStageView {
  key: string;
  title: string;
  description: string;
  status: ScriptedStageStatus;
  duration_seconds: number;
}

interface InternalStageState {
  status: ScriptedStageStatus;
  startAt: number | null;
  endAt: number | null;
  durationMs: number; // durasi acak final; tahap terakhir = durasi minimum saja
  pauseMs: number;
}

function randBetween(min: number, max: number) {
  return min + Math.random() * (max - min);
}

function easeOutQuad(t: number) {
  return 1 - (1 - t) * (1 - t);
}

function easeInQuad(t: number) {
  return t * t;
}

const LAST_INDEX = SCRIPTED_STAGE_DEFS.length - 1;

/**
 * Index tahap "Menyiapkan Data Artikel" -- secara konsep merepresentasikan
 * proses scraping/pengumpulan data artikel. Kalau backend melaporkan hasil
 * KOSONG (kata kunci tidak ada di database/scraping), animasi tidak perlu
 * dilanjutkan ke tahap TF-IDF/cosine similarity karena memang tidak ada
 * artikel untuk diproses -- jadi progress bar dihentikan tepat di tahap ini.
 */
const SCRAPING_STOP_INDEX = 1;

export type ScriptedResultStatus = "pending" | "found" | "empty";

export function useScriptedStages(
  isComplete: boolean,
  isActive: boolean,
  startedAt: number | null,
  resultStatus: ScriptedResultStatus = "pending",
) {
  const [, bump] = useState(0);
  const stateRef = useRef<InternalStageState[]>([]);
  const initializedRef = useRef(false);
  const emptyHaltedRef = useRef(false);

  // Inisialisasi jadwal sekali per sesi pencarian (durasi & jeda diacak tiap sesi).
  useEffect(() => {
    if (!isActive || startedAt === null) {
      if (!isActive) {
        initializedRef.current = false;
        stateRef.current = [];
        emptyHaltedRef.current = false;
      }
      return;
    }
    if (initializedRef.current) return;
    initializedRef.current = true;
    emptyHaltedRef.current = false;

    stateRef.current = SCRIPTED_STAGE_DEFS.map((def, i) => ({
      status: i === 0 ? "running" : "waiting",
      startAt: i === 0 ? startedAt : null,
      endAt: null,
      durationMs: randBetween(def.minMs, def.maxMs),
      pauseMs: def.pause ? randBetween(150, 320) : 0,
    }));
  }, [isActive, startedAt]);

  // Detak 100ms untuk menggerakkan timeline & menyegarkan angka waktu.
  useEffect(() => {
    if (!isActive) return;

    const id = window.setInterval(() => {
      if (
        initializedRef.current &&
        startedAt !== null &&
        !emptyHaltedRef.current
      ) {
        const now = Date.now();
        const states = stateRef.current;

        for (let i = 0; i < states.length; i++) {
          const st = states[i];
          if (st.status !== "running" || !st.startAt) continue;

          const isLast = i === LAST_INDEX;
          const elapsedInStage = now - st.startAt;

          // Hasil kosong: begitu tahap scraping ("dataset") mencapai durasi
          // minimumnya, hentikan seluruh animasi di sini -- jangan lanjut ke
          // tahap berikutnya (cleaning, TF-IDF, dst).
          if (resultStatus === "empty" && i >= SCRAPING_STOP_INDEX) {
            if (elapsedInStage >= st.durationMs) {
              st.status = "done";
              st.endAt = now;
              emptyHaltedRef.current = true;
            }
            continue;
          }

          if (isLast) {
            // Tahap terakhir hanya "selesai" kalau backend benar-benar complete
            // DAN durasi minimumnya sudah lewat.
            if (isComplete && elapsedInStage >= st.durationMs) {
              st.status = "done";
              st.endAt = now;
            }
          } else if (elapsedInStage >= st.durationMs) {
            st.status = "done";
            st.endAt = now;
            const next = states[i + 1];
            if (next && next.status === "waiting") {
              next.status = "running";
              next.startAt = now;
            }
          }
        }
      }
      bump((t) => (t + 1) % 1_000_000);
    }, 100);

    return () => window.clearInterval(id);
  }, [isActive, isComplete, startedAt, resultStatus]);

  const now = Date.now();
  const states = stateRef.current;

  const stages: ScriptedStageView[] = SCRIPTED_STAGE_DEFS.map((def, i) => {
    const st = states[i];
    if (!st)
      return {
        key: def.key,
        title: def.title,
        description: def.description,
        status: "waiting",
        duration_seconds: 0,
      };

    let seconds = 0;
    if (st.status === "running" && st.startAt) {
      seconds = (now - st.startAt) / 1000;
    } else if (st.status === "done" && st.startAt && st.endAt) {
      seconds = (st.endAt - st.startAt) / 1000;
    }

    return {
      key: def.key,
      title: def.title,
      description: def.description,
      status: st.status,
      duration_seconds: seconds,
    };
  });

  const elapsedSeconds = startedAt ? (now - startedAt) / 1000 : 0;

  // Hitung persentase keseluruhan mengikuti kurva per-band (lihat komentar di atas).
  let percent = 0;
  if (states.length > 0 && startedAt) {
    const runningIndex = states.findIndex((s) => s.status === "running");
    const allDone = states.every((s) => s.status === "done");

    if (allDone) {
      percent = 100;
    } else if (runningIndex === -1) {
      // Tidak ada tahap yang sedang berjalan. Ini normal di awal (percent 0),
      // tapi juga terjadi saat animasi dihentikan lebih awal karena hasil
      // kosong (berhenti di tahap scraping) -- pada kondisi itu, tampilkan
      // persentase akhir dari tahap terakhir yang benar-benar selesai,
      // bukan mundur ke 0%.
      let lastDoneEnd = 0;
      for (let i = 0; i < states.length; i++) {
        if (states[i].status === "done") {
          lastDoneEnd = SCRIPTED_STAGE_DEFS[i].percentEnd;
        }
      }
      percent = lastDoneEnd;
    } else {
      const def = SCRIPTED_STAGE_DEFS[runningIndex];
      const st = states[runningIndex];
      const elapsedInStage = st.startAt ? now - st.startAt : 0;
      const span = def.percentEnd - def.percentStart;

      if (runningIndex === LAST_INDEX) {
        // Band terakhir: naik cepat sampai durasi minimum, lalu merambat pelan
        // secara asimtotik sambil menunggu backend, tanpa pernah menyentuh 95%.
        const rampMs = st.durationMs;
        if (elapsedInStage <= rampMs) {
          const ratio = rampMs > 0 ? elapsedInStage / rampMs : 1;
          percent = def.percentStart + span * 0.55 * ratio;
        } else {
          const waitElapsed = elapsedInStage - rampMs;
          const K = 15000;
          const rampVal = def.percentStart + span * 0.55;
          percent =
            rampVal +
            (def.percentEnd - rampVal) * (1 - Math.exp(-waitElapsed / K));
        }
      } else {
        let ratio = Math.min(1, Math.max(0, elapsedInStage / st.durationMs));

        if (st.pauseMs > 0) {
          // Jeda singkat di awal tahap (kesan "normal dengan jeda").
          const pauseRatio = st.pauseMs / st.durationMs;
          if (ratio < pauseRatio) {
            ratio = 0;
          } else {
            ratio = (ratio - pauseRatio) / Math.max(0.0001, 1 - pauseRatio);
          }
        }

        if (def.percentEnd <= 20) {
          ratio = easeOutQuad(ratio); // band cepat
        } else if (def.percentStart >= 60) {
          ratio = easeInQuad(ratio); // band melambat
        }
        // band 20-60% dibiarkan mendekati linear (terasa "normal")

        percent = def.percentStart + span * ratio;
      }
    }
  }

  const isFinished =
    isComplete && states.length > 0 && states.every((s) => s.status === "done");

  // Ditandai selesai lebih awal karena hasil kosong: tahap scraping ("dataset")
  // sudah "done" dan tidak ada tahap lain yang sedang berjalan.
  const scrapingStage = states[SCRAPING_STOP_INDEX];
  const isEmptyHalted =
    resultStatus === "empty" &&
    !!scrapingStage &&
    scrapingStage.status === "done" &&
    !states.some((s) => s.status === "running");

  return {
    stages,
    percent: Math.min(100, Math.round(percent)),
    elapsedSeconds,
    isFinished,
    isEmptyHalted,
  };
}

/* =========================================================================
 * TYPING / TICKER HOOKS
 * ====================================================================== */

export function useTypingText(text: string, speed = 22) {
  const [shown, setShown] = useState("");

  useEffect(() => {
    setShown("");
    if (!text) return;

    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      setShown(text.slice(0, i));
      if (i >= text.length) window.clearInterval(id);
    }, speed);

    return () => window.clearInterval(id);
  }, [text, speed]);

  return shown;
}

export function useDotTicker(steps = 3, intervalMs = 380) {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const id = window.setInterval(
      () => setTick((t) => (t + 1) % steps),
      intervalMs,
    );
    return () => window.clearInterval(id);
  }, [steps, intervalMs]);

  return tick;
}

export function useMicroTicker(
  active: boolean,
  phrases: string[],
  intervalMs = 1700,
) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active || phrases.length <= 1) {
      setIndex(0);
      return;
    }
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % phrases.length);
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [active, phrases, intervalMs]);

  return phrases[index] || phrases[0] || "";
}
