UPDATE public.categories SET icon = CASE slug
  WHEN 'informatica' THEN 'laptop'
  WHEN 'componentes-pc' THEN 'cpu'
  WHEN 'almacenamiento' THEN 'hard-drive'
  WHEN 'perifericos' THEN 'keyboard'
  WHEN 'audio' THEN 'headphones'
  WHEN 'gaming-y-consolas' THEN 'gamepad-2'
  WHEN 'smartphones-y-tablets' THEN 'smartphone'
  WHEN 'tv-e-imagen' THEN 'tv'
  WHEN 'fotografia-y-video' THEN 'camera'
  WHEN 'redes' THEN 'router'
  WHEN 'domotica' THEN 'home'
  WHEN 'wearables' THEN 'watch'
  WHEN 'energia' THEN 'battery-charging'
  ELSE icon
END
WHERE parent_id IS NULL;