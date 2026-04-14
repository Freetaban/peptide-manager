-- Migration 021: Add resumed_at to cycles
-- Traccia la data dell'ultima ripresa da pausa, per escluderla dal calcolo del ritardo.

ALTER TABLE cycles ADD COLUMN resumed_at DATE;
