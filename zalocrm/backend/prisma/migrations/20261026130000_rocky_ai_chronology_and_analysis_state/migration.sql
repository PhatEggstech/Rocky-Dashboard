ALTER TABLE "rocky_ai_objects"
  ADD COLUMN "first_evidence_at" TIMESTAMP(3),
  ADD COLUMN "last_evidence_at" TIMESTAMP(3);

DROP INDEX IF EXISTS "rocky_ai_objects_org_id_conversation_id_updated_at_idx";
CREATE INDEX "rocky_ai_objects_org_id_conversation_id_last_evidence_at_idx"
  ON "rocky_ai_objects"("org_id", "conversation_id", "last_evidence_at");

CREATE TABLE "rocky_ai_conversation_analyses" (
  "id" TEXT NOT NULL,
  "org_id" TEXT NOT NULL,
  "conversation_id" TEXT NOT NULL,
  "source_conversation_id" TEXT NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'NOT_STARTED',
  "source_object_count" INTEGER NOT NULL DEFAULT 0,
  "source_message_count" INTEGER NOT NULL DEFAULT 0,
  "source_last_message_at" TIMESTAMP(3),
  "source_analysis_updated_at" TIMESTAMP(3),
  "metadata" JSONB NOT NULL DEFAULT '{}',
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "rocky_ai_conversation_analyses_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "rocky_ai_conversation_analyses_conversation_id_key"
  ON "rocky_ai_conversation_analyses"("conversation_id");
CREATE UNIQUE INDEX "rocky_ai_conversation_analyses_org_id_source_conversation_id_key"
  ON "rocky_ai_conversation_analyses"("org_id", "source_conversation_id");
CREATE INDEX "rocky_ai_conversation_analyses_org_id_status_source_last_message_at_idx"
  ON "rocky_ai_conversation_analyses"("org_id", "status", "source_last_message_at");
ALTER TABLE "rocky_ai_conversation_analyses"
  ADD CONSTRAINT "rocky_ai_conversation_analyses_conversation_id_fkey"
  FOREIGN KEY ("conversation_id") REFERENCES "conversations"("id") ON DELETE CASCADE ON UPDATE CASCADE;
