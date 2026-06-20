package desktop

// Services groups all desktop API services for Wails registration or tests.
type Services struct {
	App       *AppService
	Providers *ProviderService
	MCP       *MCPService
	Entities  *EntityService
	Tools     *ToolService
	Doctor    *DoctorService
	Config    *ConfigService
	Launch    *LaunchService
}

func NewServices(version, dbPath string) Services {
	return Services{
		App:       NewAppService(version),
		Providers: NewProviderService(dbPath),
		MCP:       NewMCPService(),
		Entities:  NewEntityService(),
		Tools:     NewToolService(),
		Doctor:    NewDoctorService(version, dbPath),
		Config:    NewConfigService(),
		Launch:    NewLaunchService(dbPath),
	}
}
