#ifndef UE4SS_SDK_BP_AnimNotify_Fire_HPP
#define UE4SS_SDK_BP_AnimNotify_Fire_HPP

class UBP_AnimNotify_Fire_C : public UAnimNotify
{

    void NewFunction();
    bool Received_Notify(class USkeletalMeshComponent* MeshComp, class UAnimSequenceBase* Animation, const FAnimNotifyEventReference& EventReference);
}; // Size: 0x38

#endif
