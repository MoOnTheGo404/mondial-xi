import { z } from "zod";

/**
 * Runtime validation for the forecast envelope at the client boundary.
 * Catches API/client drift early instead of rendering NaNs. Kept to the
 * fields the UI arithmetic depends on; extra fields pass through.
 */
const ProbabilitiesSchema = z
  .object({
    home: z.number().min(0).max(1),
    draw: z.number().min(0).max(1),
    away: z.number().min(0).max(1),
  })
  .refine(
    (p) => Math.abs(p.home + p.draw + p.away - 1) < 1e-3,
    "probabilities must sum to 1",
  );

export const PredictionCoreSchema = z
  .object({
    model_version: z.string().min(1),
    data_cutoff: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    probabilities: ProbabilitiesSchema,
    team_only_probabilities: ProbabilitiesSchema,
    expected_goals: z.object({ home: z.number().min(0), away: z.number().min(0) }),
    scenario_adjusted: z.boolean(),
    data_quality: z.object({ grade: z.enum(["A", "B", "C", "D"]) }).passthrough(),
    score_matrix: z.array(z.array(z.number())).min(5),
  })
  .passthrough();

export function parsePrediction<T>(data: T): T {
  PredictionCoreSchema.parse(data);
  return data;
}
