PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE usuarios (
	id INTEGER NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	rol VARCHAR(20) NOT NULL, 
	activo BOOLEAN, 
	fecha_registro DATETIME, 
	PRIMARY KEY (id)
);
INSERT INTO usuarios VALUES(1,'admin@mascate.org','$2b$12$/hN2CxJb17RzQZg3TT8C..4Wk5zO2dmbVbOflMapjg8tgHxqwmozK','admin',1,'2026-02-26 19:09:28.067234');
INSERT INTO usuarios VALUES(2,'artevivo@mascate.org','$2b$12$wMinI/KdprnU5RgMW81wBeOyQykiQHwLcx4EkxGAOzpG0rJxOpObS','dispositivo',1,'2026-03-13 19:09:28.067234');
INSERT INTO usuarios VALUES(3,'deportivasur@mascate.org','$2b$12$Lj1Hcd0aN.ItIZcJijk80urnQL1mrOUouuvsRju3/pDBcuq3C6hwm','dispositivo',1,'2026-03-18 19:09:28.067234');
INSERT INTO usuarios VALUES(4,'maria@mascate.org','$2b$12$vJUFYOxuYo0M4eJ1FSzldOMW6eMGdKi0SvOt1nYsUXgtTEQ7ZcEZ2','prescriptor',1,'2026-03-23 19:09:28.067234');
INSERT INTO usuarios VALUES(5,'carlos@mascate.org','$2b$12$S4FP1XdPzmNGMsxqzXQFGuODNCIcPBT.v42YlqTil.yFd0jmGZgqG','prescriptor',1,'2026-03-28 19:09:28.067234');
INSERT INTO usuarios VALUES(6,'skate@mail.com','$2b$12$Dxe1Yz7jCCqNeCwgGn1do.wLen75p9pz3qfMXv3h7CEImykhSxZcq','beneficiario',1,'2026-04-02 19:09:28.067234');
INSERT INTO usuarios VALUES(7,'sofi@mail.com','$2b$12$LUEhrzJOQzH8YvLxV2VkhuCWbp.SPzOG4Io3HMhmfR8dT8HnsbcLC','beneficiario',1,'2026-04-07 19:09:28.067234');
INSERT INTO usuarios VALUES(8,'julian@mail.com','$2b$12$adfaFpZ7RrD.VKwLGakfTeTwJsRg9OCl62BgCwNNtMMvHwy6TbEoS','beneficiario',1,'2026-04-09 19:09:28.067234');
INSERT INTO usuarios VALUES(9,'laura@mail.com','$2b$12$Id1Ic6r8IpdbEZdQOB.Ca.sR5XKF873Nkqe1Fji/5Ia71H4g.33ZS','beneficiario',1,'2026-04-12 19:09:28.067234');
CREATE TABLE dispositivos (
	id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	nombre VARCHAR(200) NOT NULL, 
	lugar_actividades VARCHAR(100), 
	ubicacion VARCHAR(300), 
	tipo_servicio VARCHAR(100), 
	dia_actividad VARCHAR(100), 
	hora_actividad VARCHAR(20), 
	telefono VARCHAR(30), 
	redes_sociales VARCHAR(300), 
	PRIMARY KEY (id), 
	UNIQUE (usuario_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);
INSERT INTO dispositivos VALUES(1,2,'Arte Vivo Techotiva','Parque','Parque El Tintal, Bogotá','Artístico','Lunes, Miércoles, Viernes','14:00','+57 310 000 0001','@artevivo_tec');
INSERT INTO dispositivos VALUES(2,3,'Red Deportiva Sur','Salón comunal','Cancha Municipal Sur, Bogotá','Deportivo','Martes, Jueves, Sábado','16:00','+57 310 000 0002','@redsur_dep');
CREATE TABLE beneficiarios (
	id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	nombre_apodo VARCHAR(200) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (usuario_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id)
);
INSERT INTO beneficiarios VALUES(1,6,'Skate');
INSERT INTO beneficiarios VALUES(2,7,'Sofía G.');
INSERT INTO beneficiarios VALUES(3,8,'Julián M.');
INSERT INTO beneficiarios VALUES(4,9,'Laura R.');
CREATE TABLE prescriptores (
	id INTEGER NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	nombre_completo VARCHAR(200) NOT NULL, 
	perfil_disciplina VARCHAR(100), 
	telefono VARCHAR(30), 
	dispositivo_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (usuario_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id), 
	FOREIGN KEY(dispositivo_id) REFERENCES dispositivos (id)
);
INSERT INTO prescriptores VALUES(1,4,'María Pérez','Arte y cultura','+57 320 111 2222',1);
INSERT INTO prescriptores VALUES(2,5,'Carlos Ramírez','Deporte','+57 320 333 4444',2);
CREATE TABLE actividades (
	id INTEGER NOT NULL, 
	dispositivo_id INTEGER NOT NULL, 
	nombre VARCHAR(200) NOT NULL, 
	tipo VARCHAR(60), 
	lugar VARCHAR(200), 
	dia_semana VARCHAR(30), 
	hora VARCHAR(20), 
	emoji VARCHAR(10), 
	activa BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dispositivo_id) REFERENCES dispositivos (id)
);
INSERT INTO actividades VALUES(1,1,'Taller de grafiti','Artístico','Parque El Tintal','Lunes','15:00','🎨',1);
INSERT INTO actividades VALUES(2,1,'Círculo musical','Cultural','Salón comunal','Viernes','17:00','🎵',1);
INSERT INTO actividades VALUES(3,1,'Huerta urbana','Ambiental','Reserva natural','Sábado','09:00','🌿',1);
INSERT INTO actividades VALUES(4,2,'Fútbol comunitario','Deportivo','Cancha Municipal','Miércoles','16:00','⚽',1);
INSERT INTO actividades VALUES(5,2,'Centro de escucha','Escucha','Sede propia','Jueves','14:00','💬',1);
INSERT INTO actividades VALUES(6,2,'Taller de lectura','Educativo','Salón comunal','Martes','16:00','📚',1);
CREATE TABLE primer_contacto (
	id INTEGER NOT NULL, 
	beneficiario_id INTEGER NOT NULL, 
	dispositivo_id INTEGER NOT NULL, 
	fecha_contacto DATE, 
	notas TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(beneficiario_id) REFERENCES beneficiarios (id), 
	FOREIGN KEY(dispositivo_id) REFERENCES dispositivos (id)
);
INSERT INTO primer_contacto VALUES(1,1,1,'2026-04-17','Primer acercamiento de Skate al dispositivo.');
INSERT INTO primer_contacto VALUES(2,2,1,'2026-04-16','Primer acercamiento de Sofía G. al dispositivo.');
INSERT INTO primer_contacto VALUES(3,3,2,'2026-04-15','Primer acercamiento de Julián M. al dispositivo.');
CREATE TABLE seguimientos (
	id INTEGER NOT NULL, 
	prescriptor_id INTEGER NOT NULL, 
	beneficiario_id INTEGER NOT NULL, 
	tipo_registro VARCHAR(60), 
	observaciones TEXT, 
	fecha DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(prescriptor_id) REFERENCES prescriptores (id), 
	FOREIGN KEY(beneficiario_id) REFERENCES beneficiarios (id)
);
INSERT INTO seguimientos VALUES(1,1,1,'Sesión grupal','Participó activamente en el taller.','2026-04-26 19:09:28.067234');
INSERT INTO seguimientos VALUES(2,1,2,'Seguimiento individual','Muestra interés en música.','2026-04-25 19:09:28.067234');
INSERT INTO seguimientos VALUES(3,1,3,'Sesión grupal','Asistió al taller de grafiti.','2026-04-22 19:09:28.067234');
INSERT INTO seguimientos VALUES(4,1,4,'Actividad especial','No asiste desde hace días.','2026-04-17 19:09:28.067234');
INSERT INTO seguimientos VALUES(5,2,3,'Sesión grupal','Buen rendimiento en fútbol.','2026-04-26 19:09:28.067234');
INSERT INTO seguimientos VALUES(6,2,4,'Seguimiento individual','Retomó actividades deportivas.','2026-04-23 19:09:28.067234');
CREATE TABLE inscripciones (
	id INTEGER NOT NULL, 
	beneficiario_id INTEGER NOT NULL, 
	actividad_id INTEGER NOT NULL, 
	fecha_inscripcion DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(beneficiario_id) REFERENCES beneficiarios (id), 
	FOREIGN KEY(actividad_id) REFERENCES actividades (id)
);
INSERT INTO inscripciones VALUES(1,1,1,'2026-04-27 19:09:30.118456');
INSERT INTO inscripciones VALUES(2,1,4,'2026-04-27 19:09:30.118461');
INSERT INTO inscripciones VALUES(3,2,1,'2026-04-27 19:09:30.118462');
INSERT INTO inscripciones VALUES(4,2,2,'2026-04-27 19:09:30.118463');
INSERT INTO inscripciones VALUES(5,3,4,'2026-04-27 19:09:30.118463');
INSERT INTO inscripciones VALUES(6,3,5,'2026-04-27 19:09:30.118464');
INSERT INTO inscripciones VALUES(7,4,2,'2026-04-27 19:09:30.118465');
INSERT INTO inscripciones VALUES(8,4,6,'2026-04-27 19:09:30.118465');
CREATE UNIQUE INDEX ix_usuarios_email ON usuarios (email);
CREATE INDEX ix_usuarios_id ON usuarios (id);
CREATE INDEX ix_dispositivos_id ON dispositivos (id);
CREATE INDEX ix_beneficiarios_id ON beneficiarios (id);
CREATE INDEX ix_prescriptores_id ON prescriptores (id);
CREATE INDEX ix_actividades_id ON actividades (id);
CREATE INDEX ix_primer_contacto_id ON primer_contacto (id);
CREATE INDEX ix_seguimientos_id ON seguimientos (id);
CREATE INDEX ix_inscripciones_id ON inscripciones (id);
COMMIT;
