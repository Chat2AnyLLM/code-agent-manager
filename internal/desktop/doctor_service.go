package desktop

import (
	"context"

	"github.com/chat2anyllm/code-agent-manager/internal/appapi"
	"github.com/chat2anyllm/code-agent-manager/internal/doctor"
)

type DoctorService struct {
	version string
	dbPath  string
}

func NewDoctorService(version, dbPath string) *DoctorService {
	return &DoctorService{version: version, dbPath: dbPath}
}

func (s *DoctorService) ListChecks() []string {
	return doctor.SortedNames(s.checks())
}

func (s *DoctorService) RunChecks(ctx context.Context) ([]DoctorCheckDTO, error) {
	checks := s.checks()
	out := make([]DoctorCheckDTO, 0, len(checks))
	for _, check := range checks {
		reporter := &collectingReporter{}
		res := check.Run(ctx, reporter)
		out = append(out, DoctorCheckDTO{Name: check.Name(), Issues: res.Issues, Messages: reporter.messages})
	}
	return out, nil
}

func (s *DoctorService) checks() []doctor.Check {
	api := appapi.ProviderAPI{}
	file, _ := api.File(context.Background())
	return []doctor.Check{
		doctor.InstallationCheck{Version: s.version},
		doctor.ConfigCheck{Path: s.dbPath},
		doctor.EnvCheck{},
		doctor.EndpointFormatCheck{File: file},
		doctor.CacheCheck{},
		doctor.GeminiAuthCheck{},
		doctor.CopilotAuthCheck{},
		doctor.ToolsAvailableCheck{},
	}
}

type collectingReporter struct {
	messages []DoctorMessageDTO
}

func (r *collectingReporter) Header(text string) {
	r.messages = append(r.messages, DoctorMessageDTO{Level: "header", Text: text})
}
func (r *collectingReporter) Info(text string) {
	r.messages = append(r.messages, DoctorMessageDTO{Level: "info", Text: text})
}
func (r *collectingReporter) Pass(text string) {
	r.messages = append(r.messages, DoctorMessageDTO{Level: "pass", Text: text})
}
func (r *collectingReporter) Warn(text, hint string) {
	r.messages = append(r.messages, DoctorMessageDTO{Level: "warn", Text: text, Hint: hint})
}
func (r *collectingReporter) Fail(text, hint string) {
	r.messages = append(r.messages, DoctorMessageDTO{Level: "fail", Text: text, Hint: hint})
}
