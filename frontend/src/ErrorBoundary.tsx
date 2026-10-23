import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  resetKey?: string | null;
  onReload?: () => void;
  onRecover?: () => void;
}

interface State {
  error: Error | null;
}

export class SectionErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo) {
    // Keep the failure local to this section; the run and navigation remain available.
  }

  componentDidUpdate(previous: Props) {
    if (previous.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  private reload = () => {
    this.setState({ error: null });
    this.props.onReload?.();
  };

  private recover = () => {
    this.setState({ error: null });
    this.props.onRecover?.();
  };

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <section className="section-error-boundary" role="alert">
        <strong>Không hiển thị được phần này</strong>
        <p>Run vẫn được lưu. Tải lại snapshot hoặc nạp câu hỏi vào biểu mẫu để chỉnh trước khi chạy lại.</p>
        <div>
          {this.props.onReload && <button type="button" onClick={this.reload}>Tải lại run</button>}
          {this.props.onRecover && <button type="button" onClick={this.recover}>Chỉnh câu hỏi</button>}
        </div>
      </section>
    );
  }
}
