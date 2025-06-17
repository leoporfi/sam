-- Add a new nullable column ProgramacionId to dbo.Asignaciones
ALTER TABLE dbo.Asignaciones
ADD ProgramacionId INT NULL;

-- Add a foreign key constraint to the new ProgramacionId column,
-- referencing the ProgramacionId column in the dbo.Programaciones table.
ALTER TABLE dbo.Asignaciones
ADD CONSTRAINT FK_Asignaciones_Programaciones FOREIGN KEY (ProgramacionId)
REFERENCES dbo.Programaciones(ProgramacionId);
