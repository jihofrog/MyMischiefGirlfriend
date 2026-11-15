// Experiment only (ToonTest_01 v6 eyes): painted eye textures with a soft toon light response (same sun as the skin).
// _Mode 0: UV0 texture (lash band, A / v5g iris), 1: eyeball - r30 eye front projected from object space and turned about
// the vertical axis by _GazeYaw (radians, + = character left), 2: flat _BaseColor. _Clip: alpha cut at 0.5.
// Object space of the FBX (bake_space_transform): Blender x = -X, y = -Z, z = Y.
Shader "MMGExp/AnimeToonEye"
{
    Properties
    {
        _BaseMap ("Texture", 2D) = "white" {}
        _BaseColor ("Colour", Color) = (1, 1, 1, 1)
        _Mode ("Mode (0 uv, 1 eyeball, 2 flat)", Float) = 0
        _Clip ("Alpha clip (0/1)", Float) = 0
        _LitLo ("Light low", Range(0, 1)) = 0.8
        _LitMid ("Light mid", Range(0, 1)) = 0.93
        _LightDir ("Light direction (world)", Vector) = (-0.3, 0.8, -0.5, 0)
        _GazeYaw ("Gaze yaw (rad)", Float) = 0
        _Proj ("Eyeball projection (su, tu, sv, tv)", Vector) = (1, 0, 1, 0)
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" }
        Pass
        {
            Tags { "LightMode" = "UniversalForward" }
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST; half4 _BaseColor; float _Mode, _Clip, _LitLo, _LitMid, _GazeYaw; float4 _LightDir, _Proj;
            CBUFFER_END
            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct V { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 normalWS : TEXCOORD1; float3 posOS : TEXCOORD2; };
            V vert(A i)
            {
                V o;
                o.positionCS = TransformObjectToHClip(i.positionOS.xyz);
                o.uv = i.uv; o.normalWS = TransformObjectToWorldNormal(i.normalOS); o.posOS = i.positionOS.xyz;
                return o;
            }
            half4 frag(V i) : SV_Target
            {
                float2 uv = i.uv;
                if (_Mode > 0.5 && _Mode < 1.5)
                {
                    float3 b = float3(-i.posOS.x, -i.posOS.z, i.posOS.y);
                    float a = -_GazeYaw, c = cos(a), s = sin(a);
                    uv = float2((b.x * c - b.y * s) * _Proj.x + _Proj.y, b.z * _Proj.z + _Proj.w);
                }
                half4 t = _Mode > 1.5 ? _BaseColor : SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uv) * _BaseColor;
                if (_Clip > 0.5) clip(t.a - 0.5);
                float l = saturate(dot(normalize(i.normalWS), normalize(_LightDir.xyz)));
                float lit = l < 0.45 ? lerp(_LitLo, _LitMid, smoothstep(0.15, 0.45, l)) : lerp(_LitMid, 1.0, smoothstep(0.45, 0.75, l));
                return half4(t.rgb * lit, 1);
            }
            ENDHLSL
        }
    }
}
