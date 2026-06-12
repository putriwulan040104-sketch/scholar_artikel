import { ShieldCheck, User, UsersRound } from "lucide-react";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface UserStatCardsProps {
  totalUsers: number;
  regularUserCount: number;
  superAdminCount: number;
}

export function UserStatCards({
  totalUsers,
  regularUserCount,
  superAdminCount,
}: UserStatCardsProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <Card>
        <CardHeader className="p-4 sm:p-6">
          <CardDescription>Total Pengguna</CardDescription>
          <CardTitle className="flex items-center gap-2 text-2xl sm:text-3xl">
            <UsersRound className="h-5 w-5 text-primary sm:h-6 sm:w-6" />
            {totalUsers}
          </CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="p-4 sm:p-6">
          <CardDescription>Total User</CardDescription>
          <CardTitle className="flex items-center gap-2 text-2xl sm:text-3xl">
            <User className="h-5 w-5 text-primary sm:h-6 sm:w-6" />
            {regularUserCount}
          </CardTitle>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader className="p-4 sm:p-6">
          <CardDescription>Super Admin</CardDescription>
          <CardTitle className="flex items-center gap-2 text-2xl sm:text-3xl">
            <ShieldCheck className="h-5 w-5 text-primary sm:h-6 sm:w-6" />
            {superAdminCount}
          </CardTitle>
        </CardHeader>
      </Card>
    </div>
  );
}
