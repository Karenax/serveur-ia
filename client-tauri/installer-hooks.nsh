!macro NSIS_HOOK_PREINSTALL
  Push $0
  Push $1
  Push $2
  ClearErrors
  ${GetOptions} $CMDLINE "/KIARA-WAIT=" $0
  ${IfNot} ${Errors}
    ; A running Kiara launches this installer only after saving its data.
    ; Wait for Kiara to release its executable and stop the relay before replacing them.
    System::Call 'kernel32::OpenProcess(i 0x00100000, i 0, i r0) p .r1 ?e'
    Pop $2
    ${If} $1 P<> 0
      System::Call 'kernel32::WaitForSingleObject(p r1, i 30000) i .r2'
      System::Call 'kernel32::CloseHandle(p r1)'
    ${ElseIf} $2 = 87
      StrCpy $2 0 ; The process has already exited.
    ${EndIf}
    ${If} $2 != 0
      MessageBox MB_OK|MB_ICONEXCLAMATION "Kiara est encore ouvert. Fermez Kiara puis relancez la mise à jour." /SD IDOK
      SetErrorLevel 1
      Abort
    ${EndIf}
  ${EndIf}
  Pop $2
  Pop $1
  Pop $0
!macroend
