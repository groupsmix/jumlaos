export const ROLES = ["owner", "manager", "staff", "accountant", "driver"] as const;
export type Role = (typeof ROLES)[number];

export const ROLE_LABELS_AR: Record<Role, string> = {
  owner: "مالك",
  manager: "مدير",
  staff: "موظف",
  accountant: "محاسب",
  driver: "موزع",
};

export const ROLE_LABELS_FR: Record<Role, string> = {
  owner: "Propriétaire",
  manager: "Gestionnaire",
  staff: "Employé",
  accountant: "Comptable",
  driver: "Livreur",
};
