#ifndef UE4SS_SDK_BPC_AIMove_HPP
#define UE4SS_SDK_BPC_AIMove_HPP

class UBPC_AIMove_C : public UActorComponent
{
    FPointerToUberGraphFrame UberGraphFrame;                                          // 0x00A0 (size: 0x8)
    class ABP_Spline_C* Spline;                                                       // 0x00A8 (size: 0x8)
    double Speed;                                                                     // 0x00B0 (size: 0x8)
    double DistanceAlongSpline;                                                       // 0x00B8 (size: 0x8)
    bool isLoop;                                                                      // 0x00C0 (size: 0x1)
    class AActor* Move Actor;                                                         // 0x00C8 (size: 0x8)
    bool isDead;                                                                      // 0x00D0 (size: 0x1)
    double Pitch Rotation Angle;                                                      // 0x00D8 (size: 0x8)
    double Yaw RotationAngle;                                                         // 0x00E0 (size: 0x8)
    FVector Mesh Scale;                                                               // 0x00E8 (size: 0x18)

    void ReceiveTick(float DeltaSeconds);
    void Dead();
    void ExecuteUbergraph_BPC_AIMove(int32 EntryPoint);
}; // Size: 0x100

#endif
