// Core API types shared between web app and UI components.

export interface Team {
  team_id: string;
  name: string;
  flag_code: string | null;
  confederation: string;
  is_historical: boolean;
  elo: number | null;
  matches_played: number;
}

export interface MatchRow {
  match_id: string;
  date: string;
  home: Team;
  away: Team;
  home_score: number | null;
  away_score: number | null;
  tournament: string;
  tier: string | null;
  city: string | null;
  country: string | null;
  neutral: boolean;
  shootout_winner_id: string | null;
  status?: "scheduled" | "finished";
  home_team_name_then?: string | null;
  away_team_name_then?: string | null;
}

export interface Probabilities {
  home: number;
  draw: number;
  away: number;
}

export interface Explanation {
  factor: string;
  text: string;
  direction: string;
  magnitude: number;
}

export interface PlayerAssumption {
  player_id: string;
  name?: string;
  status: string;
  availability_prob?: number;
  share_effect?: number;
}

export interface Prediction {
  model_version: string;
  champion_model: string;
  data_cutoff: string;
  teams: { home: Team | string; away: Team | string };
  context: { neutral: boolean; importance: number };
  probabilities: Probabilities;
  team_only_probabilities: Probabilities;
  scenario_adjusted: boolean;
  expected_goals: { home: number; away: number };
  base_expected_goals: { home: number; away: number };
  score_matrix: number[][];
  top_scorelines: { home: number; away: number; prob: number }[];
  clean_sheet_home: number;
  clean_sheet_away: number;
  btts: number;
  over_2_5: number;
  under_2_5: number;
  knockout: {
    p_extra_time: number;
    p_shootout: number;
    advance_home: number;
    advance_away: number;
    shootout_model: string;
  };
  player_assumptions: { home: PlayerAssumption[]; away: PlayerAssumption[] };
  elo: { home: number; away: number; diff_effective: number };
  uncertainty: { normalized_entropy: number };
  data_quality: { grade: string; reasons: string[] };
  warnings: string[];
  explanations: Explanation[];
  kind?: string;
  label?: string;
}

export interface Player {
  player_id: string;
  name: string;
  team_id: string;
  team?: Team;
  goals: number;
  penalties: number;
  first_goal: string;
  last_goal: string;
  matches_scored_in: number;
  team_matches_active: number;
  raw_goals_per_match: number;
  attack_impact: number;
  attack_impact_recent: number;
  recent_goals: number;
  team_recent_goals: number;
  goal_share_recent: number;
  coverage_pct: number;
  possible_name_collision: boolean;
  recently_active: boolean;
  shrinkage_weight: number;
  availability?: { status: string; source: string | null; note: string };
  impact_note?: string;
}

export interface ProviderStatus {
  name: string;
  kind: string;
  available: boolean;
  capabilities: string[];
  license_note: string;
  last_sync: string | null;
  detail: string | null;
  attribution: string | null;
}

export interface SimTeamResult {
  team_id: string;
  team: Team;
  reach: Record<string, number>;
  group_rank_dist: number[];
}

export interface SimulationResult {
  tournament_id: string;
  n_sims: number;
  seed: number;
  mode: string;
  elapsed_ms: number;
  model_version: string;
  data_cutoff: string;
  teams: SimTeamResult[];
  locked_applied: { round: string; team_a: string; team_b: string; winner: string }[];
}

export interface GroupRow {
  team_id: string;
  team: Team;
  rank: number;
  played: number;
  points: number;
  gf: number;
  ga: number;
  gd: number;
}

export interface BracketMatch {
  home_id: string;
  away_id: string;
  home: Team;
  away: Team;
  home_goals?: number;
  away_goals?: number;
  winner_id?: string;
  status: "finished" | "scheduled";
  shootout?: boolean;
  date?: string;
  city?: string;
}

export interface Snapshot {
  id: number;
  fixture_id: string;
  generated_at: string;
  kickoff_date: string;
  home_id: string;
  away_id: string;
  home?: Team;
  away?: Team;
  model_version: string;
  data_cutoff: string;
  lineup_status: string;
  version_label: string;
  content_hash: string;
  probabilities: Probabilities;
  expected_goals: { home: number; away: number };
  result: { home: number; away: number; outcome: string } | null;
  scores: {
    p_outcome: number;
    rps: number;
    brier: number;
    log_loss: number;
    top_pick_correct: boolean;
  } | null;
}
