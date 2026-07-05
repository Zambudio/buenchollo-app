import { Link } from "@tanstack/react-router";

export function Footer() {
  return (
    <footer className="border-t border-surface-700 bg-surface-800 mt-24">
      <div className="max-w-7xl mx-auto px-6 py-12 grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
        <div className="col-span-2 md:col-span-1">
          <div className="font-bold text-lg tracking-tighter mb-3">
            BuenChollo<span className="text-cyan-glow"> Tech</span>
          </div>
          <p className="text-muted-foreground text-xs leading-relaxed">
            Puedes usar la web sin registrarte. Si creas una cuenta, usamos el acceso con Google
            solo para iniciar sesión e identificarte; no accedemos a tu Gmail ni a tus datos.
          </p>
        </div>
        <div>
          <h4 className="font-mono text-xs uppercase text-cyan-glow mb-3">Navegar</h4>
          <ul className="space-y-2 text-muted-foreground">
            <li>
              <Link to="/" className="hover:text-foreground">
                Inicio
              </Link>
            </li>
            <li>
              <Link to="/explorar" className="hover:text-foreground">
                Explorar
              </Link>
            </li>
            <li>
              <Link to="/categorias" className="hover:text-foreground">
                Categorías
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="font-mono text-xs uppercase text-cyan-glow mb-3">Cuenta</h4>
          <ul className="space-y-2 text-muted-foreground">
            <li>
              <Link to="/login" className="hover:text-foreground">
                Acceder
              </Link>
            </li>
            <li>
              <Link to="/registro" className="hover:text-foreground">
                Crear cuenta
              </Link>
            </li>
            <li>
              <Link to="/alertas" className="hover:text-foreground">
                Mis alertas
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="font-mono text-xs uppercase text-cyan-glow mb-3">Info</h4>
          <ul className="space-y-2 text-muted-foreground">
            <li>
              <Link to="/contacto" className="hover:text-foreground">
                Contacto
              </Link>
            </li>
            <li>
              <Link to="/politica-de-privacidad" className="hover:text-foreground">
                Política de privacidad
              </Link>
            </li>
            <li>
              <Link to="/terminos-y-condiciones" className="hover:text-foreground">
                Términos y condiciones
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <h4 className="font-mono text-xs uppercase text-cyan-glow mb-3">Aviso</h4>
          <p className="text-muted-foreground text-xs leading-relaxed">
            BuenChollo Tech contiene enlaces de afiliado. Si compras a través de ellos, recibimos
            una pequeña comisión sin coste para ti.
          </p>
        </div>
      </div>
      <div className="border-t border-surface-700 px-6 py-4 text-center text-xs font-mono text-muted-foreground">
        © {new Date().getFullYear()} BuenChollo Tech · v1.0
      </div>
    </footer>
  );
}
