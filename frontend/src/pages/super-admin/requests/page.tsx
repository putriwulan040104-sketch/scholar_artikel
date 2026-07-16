// import { useCallback, useEffect, useMemo, useState } from "react";
// import { RefreshCw } from "lucide-react";
// import {
//   getArticleRequests,
//   updateArticleRequestStatus,
//   type ArticleRequest,
//   type ArticleRequestStatus,
// } from "@/api/api";
// import { Button } from "@/components/ui/button";
// import {
//   Card,
//   CardDescription,
//   CardHeader,
//   CardTitle,
// } from "@/components/ui/card";
// import ArticleRequestTable from "./table";

// function normalizeStatus(status?: string | null): ArticleRequestStatus {
//   const value = String(status || "pending").toLowerCase();

//   if (value === "processing" || value === "done" || value === "rejected") {
//     return value;
//   }

//   return "pending";
// }

// export default function SuperAdminRequestsPage() {
//   const [requests, setRequests] = useState<ArticleRequest[]>([]);
//   const [loading, setLoading] = useState(true);
//   const [message, setMessage] = useState("");
//   const [updatingId, setUpdatingId] = useState<string | number | null>(null);

//   const pendingCount = useMemo(
//     () => requests.filter((request) => normalizeStatus(request.status) === "pending").length,
//     [requests],
//   );
//   const processingCount = useMemo(
//     () => requests.filter((request) => normalizeStatus(request.status) === "processing").length,
//     [requests],
//   );
//   const doneCount = useMemo(
//     () => requests.filter((request) => normalizeStatus(request.status) === "done").length,
//     [requests],
//   );

//   const loadRequests = useCallback(async () => {
//     setLoading(true);
//     setMessage("");

//     const result = await getArticleRequests();
//     if (result.status === "error") {
//       setRequests([]);
//       setMessage(result.message || "Gagal mengambil data request artikel.");
//       setLoading(false);
//       return;
//     }

//     setRequests(result.data || []);
//     setLoading(false);
//   }, []);

//   const handleStatusChange = async (
//     requestId: string | number,
//     status: ArticleRequestStatus,
//   ) => {
//     setUpdatingId(requestId);
//     setMessage("");

//     const result = await updateArticleRequestStatus(requestId, status);
//     setUpdatingId(null);

//     if (result.status === "error") {
//       setMessage(result.message || "Gagal memperbarui status request.");
//       return;
//     }

//     setRequests((current) =>
//       current.map((item) =>
//         String(item.id) === String(requestId)
//           ? {
//               ...item,
//               ...(result.data || {}),
//               status,
//             }
//           : item,
//       ),
//     );
//     setMessage(result.message || "Status request berhasil diperbarui.");
//   };

//   useEffect(() => {
//     const timeoutId = window.setTimeout(() => {
//       void loadRequests();
//     }, 0);

//     return () => window.clearTimeout(timeoutId);
//   }, [loadRequests]);

//   return (
//     <div className="flex w-full min-w-0 max-w-full flex-1 flex-col gap-4 px-0 py-3 sm:gap-6 sm:px-4 sm:py-4 lg:px-6">
//       <div className="flex justify-stretch sm:justify-end">
//         <Button
//           onClick={loadRequests}
//           disabled={loading}
//           className="w-full sm:w-fit"
//         >
//           <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
//           {loading ? "Memuat..." : "Refresh Data"}
//         </Button>
//       </div>

//       <div className="grid min-w-0 gap-2 grid-cols-4">
//         <Card>
//           <CardHeader className="p-4 sm:p-6">
//             <CardDescription>Total Request</CardDescription>
//             <CardTitle className="text-2xl sm:text-3xl">
//               {requests.length}
//             </CardTitle>
//           </CardHeader>
//         </Card>
//         <Card>
//           <CardHeader className="p-4 sm:p-6">
//             <CardDescription>Pending</CardDescription>
//             <CardTitle className="text-2xl sm:text-3xl">
//               {pendingCount}
//             </CardTitle>
//           </CardHeader>
//         </Card>
//         <Card>
//           <CardHeader className="p-4 sm:p-6">
//             <CardDescription>Diproses</CardDescription>
//             <CardTitle className="text-2xl sm:text-3xl">
//               {processingCount}
//             </CardTitle>
//           </CardHeader>
//         </Card>
//         <Card>
//           <CardHeader className="p-4 sm:p-6">
//             <CardDescription>Selesai</CardDescription>
//             <CardTitle className="text-2xl sm:text-3xl">
//               {doneCount}
//             </CardTitle>
//           </CardHeader>
//         </Card>
//       </div>

//       {message ? (
//         <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
//           {message}
//         </div>
//       ) : null}

//       <ArticleRequestTable
//         requests={requests}
//         loading={loading}
//         updatingId={updatingId}
//         onStatusChange={handleStatusChange}
//       />
//     </div>
//   );
// }
