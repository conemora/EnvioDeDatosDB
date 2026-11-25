CREATE TABLE public.puntos_limpios (
    punto_id VARCHAR(12) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    comuna VARCHAR(60) NOT NULL,
    region VARCHAR(60) NOT NULL,
    capacidad_kg INTEGER NOT NULL CHECK (capacidad_kg > 0),
    estado VARCHAR(20) NOT NULL CHECK (estado IN ('activo', 'mantencion')),
    materiales TEXT NOT NULL
);

CREATE TABLE public.retiros (
    retiro_id VARCHAR(15) PRIMARY KEY,
    punto_id VARCHAR(12) NOT NULL REFERENCES public.puntos_limpios(punto_id),
    fecha_retiro TIMESTAMPTZ NOT NULL,
    material VARCHAR(20) NOT NULL,
    kg NUMERIC(10,2) NOT NULL CHECK (kg > 0),
    transportista VARCHAR(80) NOT NULL,
    estado VARCHAR(20) NOT NULL CHECK (estado IN ('recibido', 'validado', 'observado'))
);
