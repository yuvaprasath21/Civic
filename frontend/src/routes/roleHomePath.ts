import type { UserRole } from "@/types/domain";

export function roleHomePath(role: UserRole): string {
  switch (role) {
    case "CITIZEN": return "/dashboard";
    case "FIELD_STAFF": return "/staff/dashboard";
    case "DEPARTMENT_ADMIN":
    case "SUPER_ADMIN": return "/admin/dashboard";
    default: return "/";
  }
}
