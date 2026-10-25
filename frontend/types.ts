export type CommitmentType = "assignment" | "work" | "event" | "personal";

export interface User {
  id: number;
  email: string;
}

export interface Commitment {
  id: number;
  title: string;
  type: CommitmentType;
  date: string;
  start_time: string | null;
  end_time: string | null;
  description: string | null;
  completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface CommitmentInput {
  title: string;
  type: CommitmentType;
  date: string;
  start_time: string | null;
  end_time: string | null;
  description: string | null;
}

export interface ApiErrorBody {
  error: string;
}
