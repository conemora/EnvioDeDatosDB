SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';

SELECT COUNT(*) AS total_puntos
FROM public.puntos_limpios;

SELECT COUNT(*) AS total_retiros
FROM public.retiros;

-- Relacion entre puntos limpios y retiros

SELECT
    r.retiro_id,
    p.nombre,
    p.comuna,
    r.material,
    r.kg,
    r.estado
FROM public.retiros r
INNER JOIN public.puntos_limpios p
    ON r.punto_id = p.punto_id
ORDER BY r.retiro_id
LIMIT 10;

-- Total de retiros y kilogramos por comuna

SELECT
    p.comuna,
    COUNT(r.retiro_id) AS total_retiros,
    SUM(r.kg) AS total_kg
FROM public.retiros r
INNER JOIN public.puntos_limpios p
    ON r.punto_id = p.punto_id
GROUP BY p.comuna
ORDER BY total_kg DESC;

-- Total de kilogramos por material

SELECT
    material,
    COUNT(*) AS total_retiros,
    SUM(kg) AS total_kg
FROM public.retiros
GROUP BY material
ORDER BY total_kg DESC;

-- Comprobar retiros sin punto limpio

SELECT COUNT(*) AS retiros_huerfanos
FROM public.retiros r   
LEFT JOIN public.puntos_limpios p
    ON r.punto_id = p.punto_id
WHERE p.punto_id IS NULL;

-- Puntos limpios duplicados

SELECT punto_id, COUNT(*)
FROM public.puntos_limpios
GROUP BY punto_id
HAVING COUNT(*) > 1;

SELECT retiro_id, COUNT(*)
FROM public.retiros
GROUP BY retiro_id
HAVING COUNT(*) > 1;

-- Mostrar restricciones de las tablas

SELECT
    table_name,
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_schema = 'public'
AND table_name IN ('puntos_limpios', 'retiros')
ORDER BY table_name, constraint_type;

INSERT INTO public.retiros (
    retiro_id,
    punto_id,
    fecha_retiro,
    material,
    kg,
    transportista,
    estado
)
VALUES (
    'PRUEBA-001',
    'PL-001',
    NOW(),
    'vidrio',
    -50,
    'Transportista Prueba',
    'recibido'
);

INSERT INTO public.retiros (
    retiro_id,
    punto_id,
    fecha_retiro,
    material,
    kg,
    transportista,
    estado
)
VALUES (
    'PRUEBA-002',
    'PL-999',
    NOW(),
    'vidrio',
    50,
    'Transportista Prueba',
    'recibido'
);
