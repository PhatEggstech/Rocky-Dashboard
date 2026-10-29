-- Additive adapter for imported/Object-Chat AI results.  It never changes
-- source-Pancake data or native ZaloCRM conversation/message records.
CREATE TABLE "rocky_ai_objects" (
  "id" TEXT NOT NULL,
  "org_id" TEXT NOT NULL,
  "conversation_id" TEXT NOT NULL,
  "source_object_id" TEXT,
  "natural_name" TEXT NOT NULL,
  "object_type" TEXT,
  "summary" TEXT,
  "status" TEXT NOT NULL DEFAULT 'proposed',
  "confidence" DOUBLE PRECISION,
  "provider" TEXT,
  "model" TEXT,
  "analysis_version" TEXT,
  "metadata" JSONB NOT NULL DEFAULT '{}',
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "rocky_ai_objects_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "rocky_ai_objects_org_id_fkey" FOREIGN KEY ("org_id") REFERENCES "organizations"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT "rocky_ai_objects_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "conversations"("id") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE UNIQUE INDEX "rocky_ai_objects_org_id_source_object_id_key" ON "rocky_ai_objects"("org_id", "source_object_id");
CREATE INDEX "rocky_ai_objects_org_id_conversation_id_updated_at_idx" ON "rocky_ai_objects"("org_id", "conversation_id", "updated_at");

CREATE TABLE "rocky_ai_object_evidence" (
  "object_id" TEXT NOT NULL,
  "message_id" TEXT NOT NULL,
  "relation_type" TEXT NOT NULL DEFAULT 'evidence',
  "confidence" DOUBLE PRECISION,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "rocky_ai_object_evidence_pkey" PRIMARY KEY ("object_id", "message_id"),
  CONSTRAINT "rocky_ai_object_evidence_object_id_fkey" FOREIGN KEY ("object_id") REFERENCES "rocky_ai_objects"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT "rocky_ai_object_evidence_message_id_fkey" FOREIGN KEY ("message_id") REFERENCES "messages"("id") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX "rocky_ai_object_evidence_message_id_idx" ON "rocky_ai_object_evidence"("message_id");
