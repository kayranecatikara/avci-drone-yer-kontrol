#ifndef UE4SS_SDK_NaniteDisplacedMesh_HPP
#define UE4SS_SDK_NaniteDisplacedMesh_HPP

struct FNaniteDisplacedMeshDisplacementMap
{
    class UTexture2D* Texture;                                                        // 0x0000 (size: 0x8)
    float Magnitude;                                                                  // 0x0008 (size: 0x4)
    float Center;                                                                     // 0x000C (size: 0x4)

}; // Size: 0x10

struct FNaniteDisplacedMeshParams
{
}; // Size: 0x1

class UNaniteDisplacedMesh : public UObject
{
}; // Size: 0x78

class UNaniteDisplacedMeshComponent : public UStaticMeshComponent
{
    class UNaniteDisplacedMesh* DisplacedMesh;                                        // 0x05B8 (size: 0x8)

}; // Size: 0x5C0

#endif
