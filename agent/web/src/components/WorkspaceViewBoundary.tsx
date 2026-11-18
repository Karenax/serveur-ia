import {Component, type ReactNode} from 'react';
import {ErrorState} from './Ui';
import {DeferredViewLoadError, isStylesheetLoadFailure, ViewLoadRetryContext} from '../lib/retryableLazy';

/** Keep the navigation and other cached drafts available after a view fails. */
export class WorkspaceViewBoundary extends Component<{children:ReactNode; onLeave?:()=>void; leaveLabel?:string},{failed:boolean; loadFailure:boolean; stylesheetFailure:boolean; generation:number}> {
  private readonly identity = {};
  state = {failed:false, loadFailure:false, stylesheetFailure:false, generation:0};
  static getDerivedStateFromError(error: unknown) {
    return {failed:true, loadFailure:error instanceof DeferredViewLoadError, stylesheetFailure:isStylesheetLoadFailure(error)};
  }
  render() {
    if (this.state.failed) {
      const message = this.state.loadFailure
        ? 'Le chargement de cette rubrique a échoué. Si le problème persiste, enregistrez vos autres brouillons avant de recharger Kiara.'
        : 'Cette rubrique ne peut pas être affichée.';
      const cannotRetry = this.state.stylesheetFailure || (this.state.loadFailure && this.state.generation > 0);
      return <div role="alert"><ErrorState message={message} retry={cannotRetry ? undefined : ()=>this.setState(state=>({failed:false,generation:state.generation+1}))}/>
        {this.props.onLeave&&<button type="button" className="button secondary" onClick={this.props.onLeave}>{this.props.leaveLabel || 'Retour'}</button>}</div>;
    }
    return <ViewLoadRetryContext.Provider value={{identity:this.identity, generation:this.state.generation}}>{this.props.children}</ViewLoadRetryContext.Provider>;
  }
}
