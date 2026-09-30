declare module 'mammoth/mammoth.browser' {
  interface Result { value: string }
  const mammoth: { extractRawText(input: { arrayBuffer: ArrayBuffer }): Promise<Result> };
  export default mammoth;
  export function extractRawText(input: { arrayBuffer: ArrayBuffer }): Promise<Result>;
}
