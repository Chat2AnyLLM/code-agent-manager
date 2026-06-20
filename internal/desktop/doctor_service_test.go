package desktop

import (
	"context"
	"testing"
)

func TestDoctorServiceRunChecks(t *testing.T) {
	service := NewDoctorService("test", t.TempDir()+"/cam.db")

	checks, err := service.RunChecks(context.Background())
	if err != nil {
		t.Fatalf("run checks: %v", err)
	}
	if len(checks) == 0 {
		t.Fatal("expected checks")
	}
	if len(service.ListChecks()) == 0 {
		t.Fatal("expected check names")
	}
}
