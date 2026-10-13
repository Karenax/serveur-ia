/* One portable browser dependency and launch policy for the shared UI suites. */
'use strict';
exports.chromium=require(process.env.PLAYWRIGHT_MODULE||'playwright').chromium;
exports.options={headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:process.platform==='win32'?{channel:'chrome'}:{})};
