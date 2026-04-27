import { z } from "zod";
import { ROLES } from "./roles";

export const phoneSchema = z
  .string()
  .min(5)
  .max(25)
  .regex(/^[+\d\s().-]+$/, { message: "phone_invalid_chars" });

export const otpRequestSchema = z.object({
  phone: phoneSchema,
});

export const otpVerifySchema = z.object({
  phone: phoneSchema,
  code: z.string().regex(/^\d{4,8}$/, { message: "code_must_be_digits" }),
});

export const debtorCreateSchema = z.object({
  phone: phoneSchema,
  display_name: z.string().min(1).max(200),
  city: z.string().max(100).optional(),
  address_text: z.string().max(2000).optional(),
  credit_limit_centimes: z.number().int().nonnegative().default(0),
  payment_terms_days: z.number().int().min(0).max(365).default(30),
  notes: z.string().max(2000).optional(),
});

export const invoiceLineSchema = z.object({
  description: z.string().min(1).max(300),
  qty: z.number().positive(),
  unit_price_centimes: z.number().int().nonnegative(),
  vat_rate_bps: z.number().int().min(0).max(10_000).default(2000),
});

export const invoiceCreateSchema = z.object({
  debtor_id: z.number().int().positive().nullable().optional(),
  due_at: z.string().date().nullable().optional(),
  payment_terms_days: z.number().int().min(0).max(365).default(30),
  lines: z.array(invoiceLineSchema).min(1),
  notes: z.string().max(2000).optional(),
});

export const debtEventCreateSchema = z.object({
  debtor_id: z.number().int().positive(),
  kind: z.enum(["debt", "payment", "adjustment", "writeoff", "refund"]),
  amount_centimes: z.number().int().positive(),
  due_date: z.string().date().nullable().optional(),
  reference: z.string().max(128).nullable().optional(),
  raw_message: z.string().max(2000).nullable().optional(),
  source: z.enum(["whatsapp", "web", "order", "import"]).default("web"),
});

export const roleSchema = z.enum(ROLES);
