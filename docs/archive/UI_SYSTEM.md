# Sistema de Diseño e Iconografía

Este documento explica cómo se gestionan los elementos visuales y la iconografía dinámica en **BuenCholloTech**.

## 🎨 Iconografía Dinámica (Lucide React)

Para las categorías y elementos de la interfaz, utilizamos la librería **Lucide React**. A diferencia de las imágenes tradicionales, Lucide utiliza **SVG (Scalable Vector Graphics)**.

### ¿Por qué SVG?
- **Escalabilidad**: Los iconos se definen mediante coordenadas matemáticas, lo que permite ampliarlos sin pérdida de calidad.
- **Rendimiento**: El peso de los iconos es mínimo, acelerando la carga de la web.
- **Estilización**: Permite cambiar colores y tamaños directamente mediante CSS o props de React (ej: `text-cyan-glow`).

## 🛠️ Implementación del Diccionario de Iconos

Para permitir que los iconos se gestionen desde la base de datos (Supabase) sin comprometer la seguridad o el rendimiento, hemos implementado un **Icon Mapper** (Mapeador de Iconos).

### Flujo de Datos:
1. **Base de Datos**: La tabla `categories` guarda un `string` descriptivo en la columna `icon` (ej: `'laptop'`, `'energy'`).
2. **Frontend (Mapper)**: En el archivo `src/routes/index.tsx`, existe un objeto de configuración que traduce ese texto en un componente real de React:

```typescript
const ICONS: Record<string, any> = {
  laptop: Laptop,
  energy: Zap,
  cpu: Cpu,
  // ...
};
```

3. **Renderizado Dinámico**:
El componente recorre las categorías y busca su representación visual:
```typescript
const IconComponent = ICONS[category.icon] || Sparkles;
return <IconComponent className="size-6 text-cyan-glow" />;
```

## 📋 Guía de Mantenimiento

Para añadir una nueva categoría con un icono nuevo:
1. Buscar el nombre del icono en [Lucide.dev](https://lucide.dev).
2. Importar el componente en `index.tsx`.
3. Añadir la entrada al objeto `ICONS`.
4. Actualizar el registro en la base de datos con la clave elegida.

---
*Este sistema asegura que el administrador pueda cambiar la estética de las categorías desde el panel de Supabase sin necesidad de desplegar nuevo código cada vez.*
