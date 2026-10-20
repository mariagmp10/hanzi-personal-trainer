-- Esquema de base de datos para Hanzi Trainer
-- Ver PLAN.md para la explicación completa.

CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hanzi TEXT NOT NULL,
    pinyin TEXT NOT NULL,                     -- con tonos: "nǐ hǎo"
    pinyin_plain TEXT NOT NULL,               -- sin tonos, para comparar: "ni hao"
    meaning_es TEXT NOT NULL,
    meaning_en TEXT,
    hsk_level INTEGER,                        -- 1-6, aproximado por la IA; editable a mano
    radicals TEXT,                            -- JSON: ["口"] o ["女","子"] (uno por carácter del hanzi)
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',    -- 'manual' | 'photo'
    date_added TEXT NOT NULL,
    review_count INTEGER NOT NULL DEFAULT 0,
    last_reviewed_at TEXT,
    familiarity INTEGER NOT NULL DEFAULT 0,    -- sube con "lo sé", vuelve a 0 con "me cuesta"
    explanation TEXT,                          -- cómo se combinan los radicales (generado y guardado una vez)
    mnemonic TEXT                              -- truco para memorizar el carácter (idem)
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),    -- una sola fila
    hsk_level INTEGER NOT NULL DEFAULT 3
);

INSERT OR IGNORE INTO settings (id, hsk_level) VALUES (1, 3);
