/** An HTTP response was received; network and parsing errors remain ordinary errors. */
export class HttpError extends Error {
  constructor(readonly status:number, message:string) {
    super(message);
    this.name='HttpError';
  }
}
