#ifndef UE4SS_SDK_BFL_EasyInputPromptsUtilities_HPP
#define UE4SS_SDK_BFL_EasyInputPromptsUtilities_HPP

class UBFL_EasyInputPromptsUtilities_C : public UBlueprintFunctionLibrary
{

    void GetKeyCultureInvariantName(const FKey& Key, class UObject* __WorldContext, FName& KeyName, bool& KeyFound);
    void SetNewGamepadBrand(TEnumAsByte<E_GamepadBrand::Type> Gamepad Keys Brand, class UObject* __WorldContext);
    void GetGamepadBrand(class UObject* __WorldContext, TEnumAsByte<E_GamepadBrand::Type>& Gamepad Keys Brand, FString& BrandAsString);
    void GetRebindedKey(FEnhancedActionKeyMapping KeyMapping, class UObject* __WorldContext, bool& IsGamepadKey, FKey& OutKey);
    void GetInputPromptImageFromKey(class UDataTable* SearchDataTable, const FKey& Key, class UObject* __WorldContext, bool& ImageFound?, class UTexture2D*& Image);
    void GetAllKeysFromInputAction(class UInputMappingContext* InputMappingContext, class UObject* InputAction, class UObject* __WorldContext, TArray<FKey>& MNK_Keys, TArray<FKey>& GamepadKeys);
    void GetSingleKeyFromInputAction(const FS_InputActionDef& InputActionInfos, class UObject* __WorldContext, FKey& MNK_Key, FKey& GamepadKey);
    void KeyToRichTextQuery(FKey Key, bool UseTextSize?, int32 ManualSize, class UObject* __WorldContext, FText& RichTextOutput);
}; // Size: 0x28

#endif
